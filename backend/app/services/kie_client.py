"""Kie.ai HTTP client — provider communication only."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import mimetypes
import socket
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx
from fastapi import Request

from app.core.config import Settings, get_settings, reload_settings
from app.core.exceptions import KieGenerationError
from app.core.logger import get_logger

logger = get_logger()

# Cloudflare / edge gateway failures — Kie upstream is unreachable.
_EDGE_FAILURE_CODES = {520, 521, 522, 523, 524, 525, 526}
_CREDITS_CACHE_TTL_SECONDS = 45.0
_RESPONSE_BODY_LOG_LIMIT = 16_384

# Official Market model slugs:
# https://docs.kie.ai/market/bytedance/seedance-2
# https://docs.kie.ai/market/bytedance/seedance-2-fast
# https://docs.kie.ai/market/bytedance/seedance-2-mini
SEEDANCE_2_MODELS = {
    "bytedance/seedance-2",
    "bytedance/seedance-2-fast",
    "bytedance/seedance-2-mini",
}

SEEDANCE_2_RESOLUTIONS = {
    "bytedance/seedance-2": {"480p", "720p", "1080p", "4k"},
    "bytedance/seedance-2-fast": {"480p", "720p"},
    "bytedance/seedance-2-mini": {"480p", "720p"},
}

# Market card: "Seedance 1.0 Pro Fast"
# Docs: https://docs.kie.ai/market/bytedance/v1-pro-fast-image-to-video
V1_PRO_FAST_MODEL = "bytedance/v1-pro-fast-image-to-video"
V1_PRO_FAST_RESOLUTIONS = {"720p", "1080p"}
V1_PRO_FAST_DURATIONS = {5, 10}

WAN_MODEL = "wan/2-7-image-to-video"


@dataclass
class KieClient:
    """Async HTTP client for Kie.ai Image-to-Video APIs."""

    settings: Settings
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)
    _file_client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)
    _credits_cache: int | None = field(default=None, init=False, repr=False)
    _credits_cached_at: float = field(default=0.0, init=False, repr=False)
    _credits_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def startup(self) -> None:
        """Initialize the shared HTTP clients."""
        self.settings = get_settings()
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self._auth_headers(),
        }

        base_url = (self.settings.KIE_BASE_URL or "https://api.kie.ai").rstrip("/")
        file_base = (
            self.settings.KIE_FILE_BASE_URL or "https://kieai.redpandaai.co"
        ).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(self.settings.KIE_TIMEOUT),
            headers=headers,
        )
        # File Upload API uses a different host; omit Content-Type so multipart works.
        self._file_client = httpx.AsyncClient(
            base_url=file_base,
            timeout=httpx.Timeout(self.settings.KIE_TIMEOUT),
            headers={
                "Accept": "application/json",
                **self._auth_headers(),
            },
        )
        logger.info(
            "KieClient HTTP sessions created base_url='{}' file_base_url='{}' "
            "api_key='{}' timeout={}",
            base_url,
            file_base,
            self._masked_api_key(),
            self.settings.KIE_TIMEOUT,
        )

    async def shutdown(self) -> None:
        """Close the shared HTTP clients."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._file_client is not None:
            await self._file_client.aclose()
            self._file_client = None
        logger.info("KieClient HTTP sessions closed")

    async def generate_video(
        self,
        *,
        prompt: str,
        image_urls: list[str],
        model: str | None = None,
        resolution: str | None = None,
        duration_seconds: int | None = None,
    ) -> str:
        """Submit an image-to-video job to Kie.ai and return taskId."""
        self._ensure_configured()
        endpoint, payload = self._build_generate_request(
            prompt=prompt,
            image_urls=image_urls,
            model=model,
            resolution=resolution,
            duration_seconds=duration_seconds,
        )

        response = await self._send(
            "POST",
            endpoint,
            json_body=payload,
            headers=self._auth_headers(),
        )
        return self._handle_generate_response(response)

    async def get_credits(self, *, force: bool = False) -> int:
        """Fetch remaining Kie.ai account credits (cached briefly to avoid stampedes)."""
        self._ensure_configured()

        async with self._credits_lock:
            now = time.monotonic()
            if (
                not force
                and self._credits_cache is not None
                and now - self._credits_cached_at < _CREDITS_CACHE_TTL_SECONDS
            ):
                logger.info("Returning cached Kie.ai credits={}", self._credits_cache)
                return self._credits_cache

            credits = await self._fetch_credits_with_retry()
            self._credits_cache = credits
            self._credits_cached_at = time.monotonic()
            return credits

    async def _fetch_credits_with_retry(self) -> int:
        """Call Kie credits endpoint once, retry once on edge/timeout failures."""
        last_error: KieGenerationError | None = None
        for attempt in range(2):
            try:
                return await self._fetch_credits_once()
            except KieGenerationError as exc:
                last_error = exc
                if exc.code not in {
                    "kie_timeout",
                    "kie_read_timeout",
                    "kie_connect_timeout",
                    "kie_write_timeout",
                    "kie_dns_failure",
                    "kie_unavailable",
                    "kie_server_error",
                }:
                    raise
                if attempt == 0:
                    logger.warning(
                        "Kie credits attempt {} failed ({}). Retrying once…",
                        attempt + 1,
                        exc.message,
                    )
                    await asyncio.sleep(1.2)
        assert last_error is not None
        raise last_error

    async def _fetch_credits_once(self) -> int:
        # Reload key from .env so account switches apply without a full process restart.
        self.settings = reload_settings()

        response = await self._send(
            "GET",
            "/api/v1/chat/credit",
            headers=self._auth_headers(),
            # Credits should fail fast — do not inherit the long generation timeout.
            timeout=httpx.Timeout(12.0, connect=8.0),
        )

        if response.status_code in {401, 403}:
            raise KieGenerationError(
                "Kie.ai authentication failed. Check KIE_API_KEY.",
                code="kie_unauthorized",
            )
        if response.status_code == 429:
            raise KieGenerationError(
                "Kie.ai rate limit exceeded. Retry later.",
                code="kie_rate_limited",
            )
        if response.status_code in _EDGE_FAILURE_CODES:
            raise KieGenerationError(
                "Kie.ai is temporarily unreachable (gateway timeout). "
                "This is a Kie.ai/Cloudflare outage, not an invalid API key. Retry in a minute.",
                code="kie_unavailable",
            )
        if response.status_code >= 500:
            raise KieGenerationError(
                f"Kie.ai server error ({response.status_code}). Retry shortly.",
                code="kie_server_error",
            )
        if response.status_code >= 400:
            raise KieGenerationError(
                f"Kie.ai credits request rejected ({response.status_code}): "
                f"{self._safe_response_text(response)}",
                code="kie_request_rejected",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise KieGenerationError(
                "Kie.ai returned an invalid credits response",
                code="kie_invalid_response",
            ) from exc

        if not isinstance(payload, dict):
            raise KieGenerationError(
                "Kie.ai returned an unexpected credits response",
                code="kie_invalid_response",
            )

        api_code = payload.get("code")
        if isinstance(api_code, int) and api_code not in {200, 0}:
            raise KieGenerationError(
                f"Kie.ai credits request rejected: {payload.get('msg') or 'unknown error'}",
                code="kie_request_rejected",
            )

        credits = payload.get("data")
        try:
            return int(credits)
        except (TypeError, ValueError) as exc:
            raise KieGenerationError(
                "Kie.ai credits response did not include a numeric balance",
                code="kie_invalid_response",
            ) from exc

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Query Kie.ai Market task details."""
        self._ensure_configured()

        response = await self._send(
            "GET",
            "/api/v1/jobs/recordInfo",
            params={"taskId": task_id},
            headers=self._auth_headers(),
        )

        if response.status_code in {401, 403}:
            raise KieGenerationError(
                "Kie.ai authentication failed. Check KIE_API_KEY.",
                code="kie_unauthorized",
            )
        if response.status_code == 429:
            raise KieGenerationError(
                "Kie.ai rate limit exceeded. Retry later.",
                code="kie_rate_limited",
            )
        if response.status_code == 404:
            raise KieGenerationError("Kie.ai task not found", code="kie_task_not_found")
        if response.status_code >= 500:
            raise KieGenerationError(
                f"Kie.ai server error ({response.status_code})",
                code="kie_server_error",
            )
        if response.status_code >= 400:
            raise KieGenerationError(
                f"Kie.ai status request rejected ({response.status_code}): "
                f"{self._safe_response_text(response)}",
                code="kie_request_rejected",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise KieGenerationError(
                "Kie.ai returned an invalid JSON status response",
                code="kie_invalid_response",
            ) from exc

        if not isinstance(payload, dict):
            raise KieGenerationError(
                "Kie.ai returned an unexpected status response",
                code="kie_invalid_response",
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            raise KieGenerationError(
                "Kie.ai status payload missing data object",
                code="kie_invalid_response",
            )
        return data

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | float | None = None,
    ) -> httpx.Response:
        """Issue one Kie.ai HTTP call with full diagnostic logging."""
        client = self._require_client()
        request_id = uuid.uuid4().hex[:12]
        url = self._build_request_url(path, params)
        request_headers = self._effective_request_headers(headers)
        timeout_desc = self._describe_timeout(timeout)

        logger.info(
            "Kie.ai request id={} method={} url={} timeout={} headers={} body={}",
            request_id,
            method.upper(),
            url,
            timeout_desc,
            self._mask_headers(request_headers),
            self._format_json_body(json_body),
        )

        started = time.perf_counter()
        try:
            response = await client.request(
                method.upper(),
                path,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            category, code, message = self._classify_transport_error(exc)
            logger.error(
                "Kie.ai transport failure id={} category={} code={} duration_ms={:.1f} "
                "method={} url={} error={}",
                request_id,
                category,
                code,
                duration_ms,
                method.upper(),
                url,
                exc,
            )
            raise KieGenerationError(
                f"{message} [request_id={request_id}]",
                code=code,
            ) from exc

        duration_ms = (time.perf_counter() - started) * 1000.0
        category = self._classify_http_status(response.status_code)
        body_text = self._safe_response_text(response, limit=_RESPONSE_BODY_LOG_LIMIT)
        logger.info(
            "Kie.ai response id={} category={} status={} duration_ms={:.1f} "
            "method={} url={} response_headers={} body={}",
            request_id,
            category,
            response.status_code,
            duration_ms,
            method.upper(),
            str(response.request.url),
            dict(response.headers),
            body_text,
        )
        return response

    def _build_request_url(self, path: str, params: dict[str, Any] | None) -> str:
        base = (self.settings.KIE_BASE_URL or "https://api.kie.ai").rstrip("/")
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{base}{path if path.startswith('/') else f'/{path}'}"
        if params:
            return f"{url}?{urlencode(params)}"
        return url

    def _effective_request_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        client = self._require_client()
        merged: dict[str, str] = {str(k): str(v) for k, v in client.headers.items()}
        if headers:
            merged.update({str(k): str(v) for k, v in headers.items()})
        return merged

    @staticmethod
    def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
        masked: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() == "authorization":
                token = value
                prefix = ""
                if token.lower().startswith("bearer "):
                    prefix = value[:7]
                    token = value[7:]
                if len(token) <= 8:
                    masked[key] = f"{prefix}****"
                else:
                    masked[key] = f"{prefix}{'*' * 8}{token[-4:]}"
            else:
                masked[key] = value
        return masked

    @staticmethod
    def _format_json_body(body: dict[str, Any] | None) -> str:
        if body is None:
            return "null"
        try:
            return json.dumps(body, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(body)

    def _describe_timeout(self, timeout: httpx.Timeout | float | None) -> str:
        if timeout is None:
            return f"default={self.settings.KIE_TIMEOUT}s"
        if isinstance(timeout, (int, float)):
            return f"{timeout}s"
        parts = []
        for name in ("connect", "read", "write", "pool"):
            value = getattr(timeout, name, None)
            if value is not None:
                parts.append(f"{name}={value}s")
        return ", ".join(parts) if parts else str(timeout)

    @staticmethod
    def _classify_http_status(status_code: int) -> str:
        if status_code == 522:
            return "cloudflare_522"
        if status_code in _EDGE_FAILURE_CODES:
            return f"cloudflare_{status_code}"
        if 400 <= status_code < 500:
            return "http_4xx"
        if status_code >= 500:
            return "http_5xx"
        if 200 <= status_code < 300:
            return "http_2xx"
        return f"http_{status_code}"

    @staticmethod
    def _classify_transport_error(exc: Exception) -> tuple[str, str, str]:
        """Return (category, error_code, user_message) for transport failures."""
        if KieClient._is_dns_failure(exc):
            return (
                "dns_failure",
                "kie_dns_failure",
                "Kie.ai DNS resolution failed. Check network/DNS for api.kie.ai.",
            )
        if isinstance(exc, httpx.ConnectTimeout):
            return (
                "connection_timeout",
                "kie_connect_timeout",
                "Kie.ai connection timed out while establishing TCP/TLS.",
            )
        if isinstance(exc, httpx.ReadTimeout):
            return (
                "read_timeout",
                "kie_read_timeout",
                "Kie.ai read timed out waiting for the response body.",
            )
        if isinstance(exc, httpx.WriteTimeout):
            return (
                "write_timeout",
                "kie_write_timeout",
                "Kie.ai write timed out while sending the request body.",
            )
        if isinstance(exc, httpx.PoolTimeout):
            return (
                "connection_timeout",
                "kie_connect_timeout",
                "Kie.ai connection pool timed out waiting for a free connection.",
            )
        if isinstance(exc, httpx.TimeoutException):
            return (
                "timeout",
                "kie_timeout",
                "Kie.ai request timed out.",
            )
        if isinstance(exc, httpx.ConnectError):
            return (
                "connection_error",
                "kie_unavailable",
                f"Kie.ai connection failed: {exc}",
            )
        if isinstance(exc, httpx.RequestError):
            return (
                "request_error",
                "kie_unavailable",
                f"Kie.ai is unavailable: {exc}",
            )
        return (
            "unexpected_transport_error",
            "kie_unavailable",
            f"Kie.ai request failed: {exc}",
        )

    @staticmethod
    def _is_dns_failure(exc: BaseException | None) -> bool:
        markers = (
            "getaddrinfo failed",
            "name or service not known",
            "nodename nor servname",
            "temporary failure in name resolution",
            "name resolution",
            "failed to resolve",
            "could not resolve",
            "nameresolutionerror",
        )
        current: BaseException | None = exc
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, socket.gaierror):
                return True
            name = type(current).__name__.lower()
            message = str(current).lower()
            if "nameresolution" in name or any(marker in message for marker in markers):
                return True
            current = current.__cause__ or current.__context__
        return False

    def _build_generate_request(
        self,
        *,
        prompt: str,
        image_urls: list[str],
        model: str | None = None,
        resolution: str | None = None,
        duration_seconds: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Build a Market createTask request.

        Prefer Seedance 2.x when requested:
        https://docs.kie.ai/market/bytedance/seedance-2
        Fallback: Wan 2.7 I2V
        https://docs.kie.ai/market/wan/2-7-image-to-video
        """
        if not image_urls:
            raise KieGenerationError(
                "At least one public image URL is required for Kie.ai",
                code="invalid_image",
            )

        requested_model = (model or self.settings.KIE_MODEL or "").strip()
        if requested_model == V1_PRO_FAST_MODEL:
            return self._build_v1_pro_fast_request(
                prompt=prompt,
                image_urls=image_urls,
                resolution=resolution,
                duration_seconds=duration_seconds,
            )

        if requested_model in SEEDANCE_2_MODELS:
            return self._build_seedance2_request(
                model=requested_model,
                prompt=prompt,
                image_urls=image_urls,
                resolution=resolution,
                duration_seconds=duration_seconds,
            )

        if requested_model == WAN_MODEL:
            return self._build_wan_request(
                prompt=prompt,
                image_urls=image_urls,
                resolution=resolution,
                duration_seconds=duration_seconds,
            )

        if requested_model:
            logger.warning(
                "Unsupported Kie model '{}'; falling back to Seedance 1.0 Pro Fast.",
                requested_model,
            )

        # Default: market Seedance 1.0 Pro Fast (16 credits / 10s).
        return self._build_v1_pro_fast_request(
            prompt=prompt,
            image_urls=image_urls,
            resolution=resolution or "720p",
            duration_seconds=duration_seconds,
        )

    def _build_seedance2_request(
        self,
        *,
        model: str,
        prompt: str,
        image_urls: list[str],
        resolution: str | None,
        duration_seconds: int | None,
    ) -> tuple[str, dict[str, Any]]:
        """Official Seedance 2 / Fast / Mini createTask body."""
        allowed = SEEDANCE_2_RESOLUTIONS.get(model, {"480p", "720p"})
        resolved_resolution = self._normalize_seedance_resolution(resolution, allowed)
        resolved_duration = self._normalize_seedance_duration(duration_seconds)

        input_payload: dict[str, Any] = {
            "prompt": prompt[:5000],
            "first_frame_url": image_urls[0],
            "resolution": resolved_resolution,
            "aspect_ratio": "9:16",
            "duration": resolved_duration,
            "generate_audio": False,
            "return_last_frame": False,
            "web_search": False,
        }
        if len(image_urls) > 1:
            input_payload["last_frame_url"] = image_urls[-1]

        return "/api/v1/jobs/createTask", {
            "model": model,
            "input": input_payload,
        }

    def _build_v1_pro_fast_request(
        self,
        *,
        prompt: str,
        image_urls: list[str],
        resolution: str | None,
        duration_seconds: int | None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Official Seedance 1.0 Pro Fast (V1 Pro Fast I2V) body.

        Docs: https://docs.kie.ai/market/bytedance/v1-pro-fast-image-to-video
        Market pricing card: 16 Credits / 10s
        """
        raw_res = (resolution or "720p").strip().lower()
        resolved_resolution = "1080p" if raw_res in {"1080", "1080p"} else "720p"
        if resolved_resolution not in V1_PRO_FAST_RESOLUTIONS:
            resolved_resolution = "720p"

        try:
            seconds = int(str(duration_seconds if duration_seconds is not None else 5).strip())
        except (TypeError, ValueError):
            seconds = 5
        if seconds not in V1_PRO_FAST_DURATIONS:
            seconds = 10 if seconds >= 8 else 5

        return "/api/v1/jobs/createTask", {
            "model": V1_PRO_FAST_MODEL,
            "input": {
                "prompt": prompt[:10000],
                "image_url": image_urls[0],
                "resolution": resolved_resolution,
                "duration": str(seconds),
            },
        }

    def _build_wan_request(
        self,
        *,
        prompt: str,
        image_urls: list[str],
        resolution: str | None,
        duration_seconds: int | None,
    ) -> tuple[str, dict[str, Any]]:
        """Official Wan 2.7 Image-to-Video createTask body."""
        resolved_resolution = "720p" if (resolution or "").lower() in {"720", "720p"} else "1080p"
        resolved_duration = self._normalize_wan_duration(duration_seconds)

        input_payload: dict[str, Any] = {
            "prompt": prompt[:5000],
            "first_frame_url": image_urls[0],
            "resolution": resolved_resolution,
            "duration": resolved_duration,
            "prompt_extend": True,
            "watermark": False,
        }
        if len(image_urls) > 1:
            input_payload["last_frame_url"] = image_urls[-1]

        return "/api/v1/jobs/createTask", {
            "model": WAN_MODEL,
            "input": input_payload,
        }

    def _normalize_seedance_resolution(self, value: str | None, allowed: set[str]) -> str:
        raw = (value or "720p").strip().lower()
        if raw in {"4k", "2160", "2160p"}:
            raw = "4k"
        elif raw in {"1080", "1080p"}:
            raw = "1080p"
        elif raw in {"720", "720p"}:
            raw = "720p"
        elif raw in {"480", "480p"}:
            raw = "480p"
        else:
            raw = "720p"

        if raw not in allowed:
            fallback = "720p" if "720p" in allowed else sorted(allowed)[0]
            logger.warning(
                "Resolution '{}' not supported for this Seedance model; using '{}'",
                raw,
                fallback,
            )
            return fallback
        return raw

    def _normalize_seedance_duration(self, value: int | str | None) -> int:
        """Seedance 2.x docs: duration 4–15 seconds."""
        try:
            seconds = int(str(value if value is not None else self.settings.KIE_DURATION).strip())
        except (TypeError, ValueError):
            seconds = 5
        if seconds < 4:
            seconds = 4
        if seconds > 15:
            logger.warning("Duration {}s exceeds Seedance max 15s; clamping", seconds)
            seconds = 15
        return seconds

    def _normalize_wan_duration(self, value: int | str | None) -> int:
        try:
            seconds = int(str(value if value is not None else self.settings.KIE_DURATION).strip())
        except (TypeError, ValueError):
            seconds = 5
        return max(2, min(15, seconds))

    def _handle_generate_response(self, response: httpx.Response) -> str:
        """Normalize createTask responses into a task_id."""
        status_code = response.status_code
        logger.info("Kie.ai response status={}", status_code)

        if status_code in {401, 403}:
            raise KieGenerationError(
                "Kie.ai authentication failed. Check KIE_API_KEY.",
                code="kie_unauthorized",
            )
        if status_code == 429:
            raise KieGenerationError(
                "Kie.ai rate limit exceeded. Retry later.",
                code="kie_rate_limited",
            )
        if status_code >= 500:
            raise KieGenerationError(
                f"Kie.ai server error ({status_code})",
                code="kie_server_error",
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise KieGenerationError(
                "Kie.ai returned an invalid JSON response",
                code="kie_invalid_response",
            ) from exc

        if not isinstance(data, dict):
            raise KieGenerationError(
                "Kie.ai returned an unexpected response shape",
                code="kie_invalid_response",
            )

        api_code = data.get("code")
        if status_code >= 400 or (isinstance(api_code, int) and api_code not in {200, 0}):
            message = str(data.get("msg") or self._safe_response_text(response))
            raise KieGenerationError(
                f"Kie.ai request rejected: {message}",
                code="kie_request_rejected",
            )

        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        task_id = (
            payload.get("taskId")
            or payload.get("task_id")
            or payload.get("id")
            or data.get("taskId")
        )
        if not task_id:
            raise KieGenerationError(
                "Kie.ai response did not include a taskId",
                code="kie_missing_task_id",
            )

        task_id_str = str(task_id).strip()
        logger.info("Kie.ai task_id={}", task_id_str)
        return task_id_str

    def to_public_image_urls(self, image_paths: list[str]) -> list[str]:
        """
        Convert local upload paths into absolute URLs for local preview/storage.

        Prefer ensure_remote_image_urls() before createTask — Kie cannot fetch localhost.
        """
        public_base = self.settings.PUBLIC_BASE_URL.rstrip("/")
        urls: list[str] = []
        upload_root = str(self.settings.upload_path.resolve())

        for path in image_paths:
            normalized = path.replace("\\", "/")
            if normalized.startswith("http://") or normalized.startswith("https://"):
                urls.append(normalized)
                continue

            filename = normalized.rsplit("/", 1)[-1]
            if "/uploads/" in normalized:
                relative = normalized.split("/uploads/", 1)[1]
            elif normalized.startswith(upload_root):
                relative = normalized[len(upload_root) :].lstrip("/\\")
            else:
                relative = filename

            urls.append(f"{public_base}/uploads/{quote(relative)}")

        return urls

    async def ensure_remote_image_urls(self, image_paths: list[str]) -> list[str]:
        """
        Return image URLs Kie.ai can download.

        Local files (and localhost/private URLs) are uploaded via the official
        File Upload API and replaced with the returned downloadUrl.
        Docs: https://docs.kie.ai/file-upload-api/quickstart
        """
        self._ensure_configured()
        remote_urls: list[str] = []

        for raw in image_paths:
            normalized = raw.strip().replace("\\", "/")
            if normalized.startswith("http://") or normalized.startswith("https://"):
                if self._is_publicly_reachable_url(normalized):
                    remote_urls.append(normalized)
                    continue
                local = self._local_path_from_url_or_path(normalized)
                if local is None:
                    raise KieGenerationError(
                        "Image URL is not publicly reachable by Kie.ai "
                        f"(localhost/private): {normalized}. "
                        "Use a local uploaded file or a public HTTPS URL.",
                        code="invalid_image",
                    )
                remote_urls.append(await self.upload_local_image(local))
                continue

            local = self._local_path_from_url_or_path(normalized)
            if local is None:
                raise KieGenerationError(
                    f"Image file not found for Kie upload: {normalized}",
                    code="invalid_image",
                )
            remote_urls.append(await self.upload_local_image(local))

        return remote_urls

    async def upload_local_image(self, path: Path) -> str:
        """
        Upload one local image via official File Stream Upload API.

        POST {KIE_FILE_BASE_URL}/api/file-stream-upload
        Returns data.downloadUrl (fallback: data.fileUrl).
        """
        self._ensure_configured()
        client = self._require_file_client()
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            raise KieGenerationError(
                f"Image file not found for Kie upload: {resolved}",
                code="invalid_image",
            )

        request_id = uuid.uuid4().hex[:12]
        mime = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        upload_name = f"{uuid.uuid4().hex}_{resolved.name}"
        upload_path = "images/lumina"
        url = f"{client.base_url}/api/file-stream-upload"
        headers = self._mask_headers(self._effective_file_headers())

        logger.info(
            "Kie.ai file upload id={} method=POST url={} timeout={} headers={} "
            "body={{file:{}, uploadPath:{}, fileName:{}}}",
            request_id,
            url,
            self.settings.KIE_TIMEOUT,
            headers,
            resolved.name,
            upload_path,
            upload_name,
        )

        started = time.perf_counter()
        try:
            with resolved.open("rb") as handle:
                response = await client.post(
                    "/api/file-stream-upload",
                    data={
                        "uploadPath": upload_path,
                        "fileName": upload_name,
                    },
                    files={
                        "file": (upload_name, handle, mime),
                    },
                )
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            category, code, message = self._classify_transport_error(exc)
            logger.error(
                "Kie.ai file upload transport failure id={} category={} code={} "
                "duration_ms={:.1f} error={}",
                request_id,
                category,
                code,
                duration_ms,
                exc,
            )
            raise KieGenerationError(
                f"{message} [request_id={request_id}]",
                code=code,
            ) from exc

        duration_ms = (time.perf_counter() - started) * 1000.0
        category = self._classify_http_status(response.status_code)
        body_text = self._safe_response_text(response, limit=_RESPONSE_BODY_LOG_LIMIT)
        logger.info(
            "Kie.ai file upload response id={} category={} status={} "
            "duration_ms={:.1f} response_headers={} body={}",
            request_id,
            category,
            response.status_code,
            duration_ms,
            dict(response.headers),
            body_text,
        )

        if response.status_code in {401, 403}:
            raise KieGenerationError(
                "Kie.ai authentication failed during file upload. Check KIE_API_KEY.",
                code="kie_unauthorized",
            )
        if response.status_code == 429:
            raise KieGenerationError(
                "Kie.ai rate limit exceeded during file upload. Retry later.",
                code="kie_rate_limited",
            )
        if response.status_code in _EDGE_FAILURE_CODES:
            raise KieGenerationError(
                "Kie.ai file upload unreachable (gateway timeout).",
                code="kie_unavailable",
            )
        if response.status_code >= 500:
            raise KieGenerationError(
                f"Kie.ai file upload server error ({response.status_code}).",
                code="kie_server_error",
            )
        if response.status_code >= 400:
            raise KieGenerationError(
                f"Kie.ai file upload rejected ({response.status_code}): {body_text}",
                code="kie_file_upload_failed",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise KieGenerationError(
                "Kie.ai file upload returned invalid JSON",
                code="kie_invalid_response",
            ) from exc

        if not isinstance(payload, dict):
            raise KieGenerationError(
                "Kie.ai file upload returned unexpected response",
                code="kie_invalid_response",
            )

        api_code = payload.get("code")
        if isinstance(api_code, int) and api_code not in {200, 0}:
            raise KieGenerationError(
                f"Kie.ai file upload rejected: {payload.get('msg') or 'unknown error'}",
                code="kie_file_upload_failed",
            )
        if payload.get("success") is False:
            raise KieGenerationError(
                f"Kie.ai file upload failed: {payload.get('msg') or 'unknown error'}",
                code="kie_file_upload_failed",
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            raise KieGenerationError(
                "Kie.ai file upload response missing data object",
                code="kie_invalid_response",
            )

        download_url = (
            data.get("downloadUrl")
            or data.get("fileUrl")
            or data.get("url")
        )
        if not isinstance(download_url, str) or not download_url.strip():
            raise KieGenerationError(
                "Kie.ai file upload did not return downloadUrl",
                code="kie_file_upload_failed",
            )

        remote_url = download_url.strip()
        logger.info(
            "Kie.ai file upload ready id={} local={} remote={}",
            request_id,
            resolved.name,
            remote_url,
        )
        return remote_url

    def _effective_file_headers(self) -> dict[str, str]:
        client = self._require_file_client()
        merged: dict[str, str] = {str(k): str(v) for k, v in client.headers.items()}
        merged.update(self._auth_headers())
        return merged

    def _require_file_client(self) -> httpx.AsyncClient:
        if self._file_client is None:
            raise KieGenerationError(
                "KieClient file-upload session is not initialized",
                code="kie_unavailable",
            )
        return self._file_client

    def _local_path_from_url_or_path(self, value: str) -> Path | None:
        upload_root = self.settings.upload_path.resolve()
        normalized = value.replace("\\", "/")

        if normalized.startswith("http://") or normalized.startswith("https://"):
            parsed = urlparse(normalized)
            path_part = parsed.path or ""
            if "/uploads/" in path_part:
                relative = path_part.split("/uploads/", 1)[1]
                candidate = (upload_root / relative).resolve()
            else:
                return None
        elif normalized.startswith("/uploads/"):
            candidate = (upload_root / normalized.removeprefix("/uploads/")).resolve()
        elif normalized.startswith("uploads/"):
            candidate = (upload_root / normalized.removeprefix("uploads/")).resolve()
        else:
            candidate = Path(normalized).expanduser().resolve()

        try:
            candidate.relative_to(upload_root)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        return candidate

    @staticmethod
    def _is_publicly_reachable_url(url: str) -> bool:
        """Reject localhost / private hosts — Kie.ai cannot download those."""
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme not in {"http", "https"}:
            return False
        host = (parsed.hostname or "").strip().lower()
        if not host:
            return False
        if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return False
        if host.endswith(".local") or host.endswith(".internal"):
            return False
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return True
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )

    def _ensure_configured(self) -> None:
        self.settings = get_settings()
        if not self.settings.KIE_API_KEY.strip():
            raise KieGenerationError(
                "KIE_API_KEY is not configured",
                code="kie_not_configured",
            )
        if not (self.settings.KIE_BASE_URL or "").strip():
            raise KieGenerationError(
                "KIE_BASE_URL is not configured",
                code="kie_not_configured",
            )

    def _auth_headers(self) -> dict[str, str]:
        key = self.settings.KIE_API_KEY.strip()
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}"}

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise KieGenerationError(
                "KieClient HTTP session is not initialized",
                code="kie_unavailable",
            )
        return self._client

    def _masked_api_key(self) -> str:
        key = self.settings.KIE_API_KEY.strip()
        if not key:
            return "(empty)"
        if len(key) <= 8:
            return "****"
        return f"{'*' * 8}{key[-4:]}"

    @staticmethod
    def _safe_response_text(response: httpx.Response, limit: int = 300) -> str:
        text = response.text.strip().replace("\n", " ")
        if not text:
            return "(empty body)"
        if len(text) <= limit:
            return text
        return f"{text[:limit]}…[truncated {len(text) - limit} chars]"


def get_kie_client(request: Request) -> KieClient:
    """Prefer the lifespan-scoped client; fall back to a fresh instance."""
    client = getattr(request.app.state, "kie_client", None)
    if isinstance(client, KieClient):
        return client
    return KieClient(settings=get_settings())
