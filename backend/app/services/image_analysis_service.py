"""Image analysis service placeholders.

TODO: Implement vision/model analysis of uploaded product references.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logger import get_logger

logger = get_logger()


@dataclass
class ImageAnalysisService:
    """Analyzes uploaded images to extract product understanding."""

    async def analyze_images(self, file_paths: list[str]) -> dict[str, Any]:
        """
        Analyze one or more reference images.

        TODO: Load images from disk / URLs.
        TODO: Call vision model or local analysis pipeline.
        TODO: Return structured attributes (object, materials, colors, framing).
        """
        logger.debug("image_analysis_service.analyze_images called with {} paths", len(file_paths))
        raise NotImplementedError("Image analysis is not implemented in Version 1")

    async def summarize_object(self, analysis: dict[str, Any]) -> str:
        """
        Produce a short natural-language object summary.

        TODO: Convert analysis payload into a concise product description.
        """
        logger.debug("image_analysis_service.summarize_object called")
        raise NotImplementedError("Object summarization is not implemented in Version 1")


def get_image_analysis_service() -> ImageAnalysisService:
    """FastAPI dependency factory for ImageAnalysisService."""
    return ImageAnalysisService()
