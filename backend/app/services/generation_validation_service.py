"""Pre-flight validation before Kie.ai submission (credit-safe)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.exceptions import VideoGenerationError
from app.core.logger import get_logger
from app.services.kie_client import (
    SEEDANCE_15_PRO_MODEL,
    SEEDANCE_15_PRO_RESOLUTIONS,
    SEEDANCE_2_MODELS,
    SEEDANCE_2_RESOLUTIONS,
    SEEDANCE_I2V_MODELS,
    V1_LITE_MODEL,
    V1_PRO_FAST_DURATIONS,
    V1_PRO_FAST_MODEL,
    V1_PRO_FAST_RESOLUTIONS,
    V1_PRO_LITE_DURATIONS,
    V1_PRO_LITE_RESOLUTIONS,
    V1_PRO_MODEL,
)
from app.services.seedance_pricing_engine import (
    SeedancePricingEngine,
    get_seedance_pricing_engine,
)

logger = get_logger()

MIN_PROMPT_LENGTH = 40
MAX_PROMPT_LENGTH = 10_000

SUPPORTED_MODELS = set(SEEDANCE_I2V_MODELS)


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    ok: bool
    message: str


@dataclass
class GenerationValidationService:
    """Validates prompt + generation settings before any Kie.ai call."""

    settings: Settings
    pricing: SeedancePricingEngine

    def validate_prompt_and_settings(
        self,
        *,
        prompt: str,
        model: str | None,
        resolution: str | None,
        duration_seconds: int | None,
        image_urls: list[str] | None = None,
        require_public_urls: bool = True,
        local_image_paths: list[str] | None = None,
    ) -> list[ValidationCheck]:
        """Run all validation checks and return structured results."""
        checks: list[ValidationCheck] = []
        checks.append(self._check_prompt(prompt))
        checks.append(self._check_model(model))
        checks.append(self._check_resolution(model, resolution))
        checks.append(self._check_duration(model, duration_seconds))

        if require_public_urls:
            checks.append(self._check_public_image_urls(image_urls or []))
        else:
            checks.append(self._check_local_images(local_image_paths or []))

        return checks

    def ensure_valid(self, checks: list[ValidationCheck]) -> None:
        """Raise VideoGenerationError when any check failed."""
        failures = [item for item in checks if not item.ok]
        if not failures:
            return
        details = "; ".join(f"{item.name}: {item.message}" for item in failures)
        raise VideoGenerationError(
            f"Generation validation failed — {details}",
            code="validation_failed",
        )

    def resolve_model(self, api_model: str | None) -> str:
        return (api_model or self.settings.KIE_MODEL or V1_PRO_MODEL).strip()

    def resolve_resolution(self, resolution: str | None) -> str:
        raw = (resolution or self.settings.KIE_RESOLUTION or "720p").strip().lower()
        if raw in {"480", "480p"}:
            return "480p"
        if raw in {"720", "720p"}:
            return "720p"
        if raw in {"1080", "1080p"}:
            return "1080p"
        if raw in {"4k", "2160", "2160p"}:
            return "4k"
        return raw

    def resolve_duration_seconds(self, duration_seconds: int | None) -> int:
        if duration_seconds is None:
            try:
                return int(str(self.settings.KIE_DURATION).strip())
            except ValueError:
                return 5
        try:
            return int(duration_seconds)
        except (TypeError, ValueError):
            return 5

    def estimate_credits(
        self,
        *,
        model: str,
        resolution: str,
        duration_seconds: int,
        client_estimate: float | int | None = None,
        model_ui_id: str | None = None,
    ) -> float:
        """
        Always calculate from SeedancePricingEngine:
        credits = credits_per_second × duration_seconds

        client_estimate is ignored for billing — kept only for mismatch logging
        against the UI display value.
        """
        quote = self.pricing.estimateCredits(
            model_ui_id or model,
            resolution,
            duration_seconds,
        )
        if quote is not None:
            if client_estimate is not None:
                try:
                    ui_value = float(client_estimate)
                except (TypeError, ValueError):
                    ui_value = None
                if ui_value is not None and abs(ui_value - quote.credits) > 1e-6:
                    logger.warning(
                        "UI credit estimate mismatch model={} duration={}s "
                        "resolution={} ui_credits={} engine_credits={}",
                        model,
                        duration_seconds,
                        resolution,
                        ui_value,
                        quote.credits,
                    )
            return quote.credits

        logger.error(
            "Seedance pricing unavailable for model={} resolution={} "
            "duration={}s — refusing invented rates",
            model,
            resolution,
            duration_seconds,
        )
        raise VideoGenerationError(
            f"Credit pricing is not configured for '{model}' "
            f"at {resolution}/{duration_seconds}s. "
            "Add credits_per_second to seedance_pricing.json before generating.",
            code="pricing_unavailable",
        )

    async def urls_are_accessible(self, urls: list[str]) -> ValidationCheck:
        """HEAD/GET probe public HTTPS URLs (no Kie.ai calls)."""
        if not urls:
            return ValidationCheck(
                name="public_image_url",
                ok=False,
                message="No public image URLs were provided.",
            )

        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0), follow_redirects=True) as client:
            for url in urls:
                if not self._looks_public_http_url(url):
                    return ValidationCheck(
                        name="public_image_url",
                        ok=False,
                        message=f"Image URL is not publicly reachable: {url}",
                    )
                try:
                    response = await client.head(url)
                    if response.status_code >= 400 or response.status_code == 405:
                        response = await client.get(url)
                    if response.status_code >= 400:
                        return ValidationCheck(
                            name="public_image_url",
                            ok=False,
                            message=f"Image URL returned HTTP {response.status_code}: {url}",
                        )
                except httpx.HTTPError as exc:
                    return ValidationCheck(
                        name="public_image_url",
                        ok=False,
                        message=f"Image URL not accessible ({exc.__class__.__name__}): {url}",
                    )

        return ValidationCheck(
            name="public_image_url",
            ok=True,
            message=f"{len(urls)} public image URL(s) accessible.",
        )

    def _check_prompt(self, prompt: str) -> ValidationCheck:
        text = (prompt or "").strip()
        if not text:
            return ValidationCheck("prompt", False, "Prompt is empty.")
        length = len(text)
        if length < MIN_PROMPT_LENGTH:
            return ValidationCheck(
                "prompt",
                False,
                f"Prompt is too short ({length} chars; minimum {MIN_PROMPT_LENGTH}).",
            )
        if length > MAX_PROMPT_LENGTH:
            return ValidationCheck(
                "prompt",
                False,
                f"Prompt is too long ({length} chars; maximum {MAX_PROMPT_LENGTH}).",
            )
        return ValidationCheck("prompt", True, f"Prompt length OK ({length} chars).")

    def _check_model(self, model: str | None) -> ValidationCheck:
        resolved = self.resolve_model(model)
        if resolved not in SUPPORTED_MODELS:
            return ValidationCheck(
                "model",
                False,
                f"Unsupported model '{resolved}'. Supported: {', '.join(sorted(SUPPORTED_MODELS))}",
            )
        return ValidationCheck("model", True, f"Model '{resolved}' is supported.")

    def _check_resolution(self, model: str | None, resolution: str | None) -> ValidationCheck:
        resolved_model = self.resolve_model(model)
        resolved = self.resolve_resolution(resolution)

        pricing_model = self.pricing.find_model(resolved_model)
        if pricing_model and pricing_model.get("resolutions"):
            allowed = {str(item).lower() for item in pricing_model["resolutions"]}
        elif resolved_model == V1_PRO_FAST_MODEL:
            allowed = V1_PRO_FAST_RESOLUTIONS
        elif resolved_model in {V1_PRO_MODEL, V1_LITE_MODEL}:
            allowed = V1_PRO_LITE_RESOLUTIONS
        elif resolved_model == SEEDANCE_15_PRO_MODEL:
            allowed = SEEDANCE_15_PRO_RESOLUTIONS
        elif resolved_model in SEEDANCE_2_RESOLUTIONS:
            allowed = SEEDANCE_2_RESOLUTIONS[resolved_model]
        else:
            allowed = set()

        if resolved not in allowed:
            return ValidationCheck(
                "resolution",
                False,
                f"Resolution '{resolved}' is not supported for '{resolved_model}'. "
                f"Allowed: {', '.join(sorted(allowed))}",
            )
        return ValidationCheck(
            "resolution",
            True,
            f"Resolution '{resolved}' is supported for '{resolved_model}'.",
        )

    def _check_duration(self, model: str | None, duration_seconds: int | None) -> ValidationCheck:
        resolved_model = self.resolve_model(model)
        seconds = self.resolve_duration_seconds(duration_seconds)

        pricing_model = self.pricing.find_model(resolved_model)
        if pricing_model:
            dmin = int(pricing_model.get("duration_min") or 1)
            dmax = int(pricing_model.get("duration_max") or 30)
            durations = {int(item) for item in (pricing_model.get("durations") or [])}
            discrete = resolved_model in {
                V1_PRO_MODEL,
                V1_LITE_MODEL,
                V1_PRO_FAST_MODEL,
            }
            if discrete and durations and seconds not in durations:
                return ValidationCheck(
                    "duration",
                    False,
                    f"Duration {seconds}s is not supported for '{resolved_model}'. "
                    f"Allowed: {', '.join(str(item) for item in sorted(durations))}.",
                )
            if seconds < dmin or seconds > dmax:
                return ValidationCheck(
                    "duration",
                    False,
                    f"Duration {seconds}s is not supported for '{resolved_model}'. "
                    f"Allowed: {dmin}–{dmax}s.",
                )
            return ValidationCheck("duration", True, f"Duration {seconds}s is supported.")

        if resolved_model == V1_PRO_FAST_MODEL:
            if seconds not in V1_PRO_FAST_DURATIONS:
                return ValidationCheck(
                    "duration",
                    False,
                    f"Duration {seconds}s is not supported for V1 Pro Fast. Allowed: 5 or 10.",
                )
        elif resolved_model in {V1_PRO_MODEL, V1_LITE_MODEL}:
            if seconds not in V1_PRO_LITE_DURATIONS:
                return ValidationCheck(
                    "duration",
                    False,
                    f"Duration {seconds}s is not supported for Seedance 1.0. Allowed: 5 or 10.",
                )
        elif resolved_model == SEEDANCE_15_PRO_MODEL:
            if seconds < 4 or seconds > 12:
                return ValidationCheck(
                    "duration",
                    False,
                    f"Duration {seconds}s is not supported for Seedance 1.5 Pro. Allowed: 4–12.",
                )
        elif resolved_model in SEEDANCE_2_MODELS:
            if seconds < 4 or seconds > 15:
                return ValidationCheck(
                    "duration",
                    False,
                    f"Duration {seconds}s is not supported for Seedance 2.x. Allowed: 4–15.",
                )

        return ValidationCheck("duration", True, f"Duration {seconds}s is supported.")

    def _check_public_image_urls(self, image_urls: list[str]) -> ValidationCheck:
        if not image_urls:
            return ValidationCheck(
                "public_image_url",
                False,
                "No public image URLs provided for Kie.ai.",
            )
        for url in image_urls:
            if not self._looks_public_http_url(url):
                return ValidationCheck(
                    "public_image_url",
                    False,
                    f"Image URL is not publicly reachable by Kie.ai: {url}",
                )
        return ValidationCheck(
            "public_image_url",
            True,
            f"{len(image_urls)} public image URL(s) look valid (scheme/host).",
        )

    def _check_local_images(self, image_paths: list[str]) -> ValidationCheck:
        if not image_paths:
            return ValidationCheck(
                "local_image",
                False,
                "No local reference images were provided.",
            )
        upload_root = self.settings.upload_path.resolve()
        for raw in image_paths:
            path = Path(raw).expanduser().resolve()
            try:
                path.relative_to(upload_root)
            except ValueError:
                return ValidationCheck(
                    "local_image",
                    False,
                    f"Image path is outside uploads directory: {raw}",
                )
            if not path.is_file():
                return ValidationCheck(
                    "local_image",
                    False,
                    f"Image file not found: {raw}",
                )
        return ValidationCheck(
            "local_image",
            True,
            f"{len(image_paths)} local reference image(s) found.",
        )

    @staticmethod
    def _looks_public_http_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme != "https":
            # Allow http only for non-local hosts in rare staging cases.
            if parsed.scheme != "http":
                return False
        host = (parsed.hostname or "").strip().lower()
        if not host:
            return False
        if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return False
        if host.endswith(".local") or host.endswith(".internal"):
            return False
        return True

    def checks_as_dicts(self, checks: list[ValidationCheck]) -> list[dict[str, Any]]:
        return [
            {"name": item.name, "ok": item.ok, "message": item.message}
            for item in checks
        ]


def get_generation_validation_service(
    settings: Settings = Depends(get_settings),
    pricing: SeedancePricingEngine = Depends(get_seedance_pricing_engine),
) -> GenerationValidationService:
    return GenerationValidationService(
        settings=settings,
        pricing=pricing,
    )
