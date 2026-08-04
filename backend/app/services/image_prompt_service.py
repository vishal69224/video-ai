"""Public prompt generation entrypoint — delegates to fashion commercial pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger
from app.services.prompt_pipeline.pipeline import (
    FashionPromptPipeline,
    get_fashion_prompt_pipeline,
)

logger = get_logger()


@dataclass
class ImagePromptService:
    """
    Stable API facade used by video/prompt routes.

    Internally runs the fashion commercial director pipeline:
    Image Analysis → Garment → Scene → Storyboard → Action → Camera →
    Prompt Builder → Validator → Optimizer.
    """

    settings: Settings
    pipeline: FashionPromptPipeline

    async def generate_prompt(
        self,
        image_paths: list[str],
        *,
        model: str | None = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
    ) -> str:
        if not image_paths:
            raise ImagePromptGenerationError(
                "At least one image path is required",
                code="invalid_image",
            )

        resolved_paths = [self._resolve_image_path(path) for path in image_paths]
        logger.info(
            "Prompt generation starting images={} model={} duration={} resolution={}",
            len(resolved_paths),
            model,
            duration_seconds,
            resolution,
        )
        prompt = await self.pipeline.generate(
            resolved_paths,
            model=model,
            duration_seconds=duration_seconds,
            resolution=resolution,
        )
        logger.info("Final commercial prompt ready ({} chars)", len(prompt))
        return prompt

    def _resolve_image_path(self, image_path: str) -> Path:
        """Map `/uploads/...` URLs or filesystem paths onto the uploads directory."""
        raw = image_path.strip()
        if not raw:
            raise ImagePromptGenerationError("Empty image path", code="invalid_image")

        upload_root = self.settings.upload_path.resolve()

        if raw.startswith("/uploads/"):
            relative = raw.removeprefix("/uploads/")
            candidate = (upload_root / relative).resolve()
        elif raw.startswith("uploads/"):
            relative = raw.removeprefix("uploads/")
            candidate = (upload_root / relative).resolve()
        else:
            candidate = Path(raw).expanduser().resolve()

        try:
            candidate.relative_to(upload_root)
        except ValueError as exc:
            raise ImagePromptGenerationError(
                f"Image path must be inside the uploads directory: {raw}",
                code="invalid_image",
            ) from exc

        if not candidate.is_file():
            raise ImagePromptGenerationError(
                f"Image file not found: {raw}",
                code="invalid_image",
            )

        extension = candidate.suffix.lower().lstrip(".")
        if extension not in self.settings.allowed_extensions:
            allowed = ", ".join(sorted(self.settings.allowed_extensions))
            raise ImagePromptGenerationError(
                f"Unsupported image type '.{extension}'. Allowed: {allowed}",
                code="invalid_image",
            )

        if candidate.stat().st_size <= 0:
            raise ImagePromptGenerationError(
                f"Image file is empty: {raw}",
                code="invalid_image",
            )

        return candidate


def get_image_prompt_service(
    settings: Settings = Depends(get_settings),
    pipeline: FashionPromptPipeline = Depends(get_fashion_prompt_pipeline),
) -> ImagePromptService:
    """FastAPI dependency factory for ImagePromptService."""
    return ImagePromptService(settings=settings, pipeline=pipeline)
