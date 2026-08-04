"""OpenRouter OpenAI-compatible vision provider."""

from __future__ import annotations

import base64
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from app.ai.providers.base_provider import BaseVisionProvider
from app.core.config import Settings
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger

logger = get_logger()


@dataclass
class OpenRouterProvider(BaseVisionProvider):
    """Vision analysis via OpenRouter chat completions API."""

    settings: Settings

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model(self) -> str:
        return self.settings.OPENROUTER_MODEL

    async def analyze_images(
        self,
        image_urls: list[str],
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
    ) -> str:
        if not image_urls:
            raise ImagePromptGenerationError(
                "At least one image is required",
                code="invalid_image",
            )

        api_key = (self.settings.OPENROUTER_API_KEY or "").strip()
        if not api_key:
            raise ImagePromptGenerationError(
                "OPENROUTER_API_KEY is not configured",
                code="invalid_api_key",
            )

        resolved_urls = [self._resolve_image_url(ref) for ref in image_urls]
        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": user_prompt},
        ]
        for url in resolved_urls:
            content_parts.append(
                {"type": "image_url", "image_url": {"url": url}}
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_parts},
            ],
            "temperature": temperature,
        }

        base_url = self.settings.OPENROUTER_BASE_URL.rstrip("/")
        endpoint = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Optional OpenRouter attribution headers (safe defaults).
            "HTTP-Referer": self.settings.PUBLIC_BASE_URL or "http://localhost",
            "X-Title": self.settings.APP_NAME or "Video AI Backend",
        }

        started = time.perf_counter()
        logger.info(
            "AI request provider={} model={} images={}",
            self.name,
            self.model,
            len(resolved_urls),
        )

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.OPENROUTER_TIMEOUT)
            ) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ImagePromptGenerationError(
                f"OpenRouter request timed out after "
                f"{self.settings.OPENROUTER_TIMEOUT:.0f}s",
                code="generation_timeout",
            ) from exc
        except httpx.RequestError as exc:
            raise ImagePromptGenerationError(
                f"OpenRouter network error: {exc}",
                code="provider_unavailable",
            ) from exc

        duration_ms = (time.perf_counter() - started) * 1000
        self._raise_for_status(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise ImagePromptGenerationError(
                "OpenRouter returned a non-JSON response",
                code="empty_response",
            ) from exc

        content = self._extract_content(data)
        logger.info(
            "AI response provider={} model={} images={} duration_ms={:.1f} "
            "response_length={} status={}",
            self.name,
            self.model,
            len(resolved_urls),
            duration_ms,
            len(content or ""),
            response.status_code,
        )
        if not content.strip():
            raise ImagePromptGenerationError(
                "OpenRouter returned an empty analysis",
                code="empty_response",
            )
        return content.strip()

    def _resolve_image_url(self, image_ref: str) -> str:
        """Convert local paths to data URLs; pass through http(s)/data URLs."""
        raw = (image_ref or "").strip()
        if not raw:
            raise ImagePromptGenerationError("Empty image path", code="invalid_image")

        lowered = raw.lower()
        if lowered.startswith(("http://", "https://", "data:")):
            return raw

        if raw.startswith("file://"):
            parsed = urlparse(raw)
            path = Path(unquote(parsed.path))
        else:
            path = Path(raw).expanduser()

        if not path.is_file():
            raise ImagePromptGenerationError(
                f"Image file not found: {image_ref}",
                code="invalid_image",
            )

        mime, _ = mimetypes.guess_type(str(path))
        if not mime or not mime.startswith("image/"):
            suffix = path.suffix.lower().lstrip(".")
            mime = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
            }.get(suffix, "image/jpeg")

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ImagePromptGenerationError(
                "OpenRouter response missing choices",
                code="empty_response",
            )
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ImagePromptGenerationError(
                "OpenRouter response missing message",
                code="empty_response",
            )
        content = message.get("content")
        if isinstance(content, list):
            # Some models return multimodal content arrays.
            texts = [
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict) and part.get("type") in {None, "text"}
            ]
            return "\n".join(part for part in texts if part).strip()
        return str(content or "").strip()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return

        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                error = body.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or error.get("code") or "")
                elif error:
                    detail = str(error)
                else:
                    detail = str(body.get("message") or "")
        except ValueError:
            detail = (response.text or "")[:200]

        suffix = f": {detail}" if detail else ""

        if status == 401:
            raise ImagePromptGenerationError(
                f"OpenRouter invalid API key{suffix}",
                code="invalid_api_key",
            )
        if status == 429:
            raise ImagePromptGenerationError(
                f"OpenRouter rate limit exceeded{suffix}",
                code="rate_limit",
            )
        if status in {500, 502, 503, 504}:
            raise ImagePromptGenerationError(
                f"OpenRouter unavailable (HTTP {status}){suffix}",
                code="provider_unavailable",
            )
        raise ImagePromptGenerationError(
            f"OpenRouter request failed (HTTP {status}){suffix}",
            code="prompt_generation_failed",
        )
