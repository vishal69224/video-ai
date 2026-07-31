"""Prompt builder service placeholders.

TODO: Build cinematic prompts from analyzed image attributes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logger import get_logger

logger = get_logger()


@dataclass
class PromptBuilderService:
    """Builds generation prompts from image analysis results."""

    async def build_prompt(self, analysis: dict[str, Any], project_name: str | None = None) -> str:
        """
        Create a cinematic video prompt.

        TODO: Map analysis fields into camera language, lighting, and motion.
        TODO: Support optional user overrides / project naming.
        """
        logger.debug(
            "prompt_builder_service.build_prompt called project_name={}",
            project_name,
        )
        raise NotImplementedError("Prompt building is not implemented in Version 1")

    async def build_negative_prompt(self, analysis: dict[str, Any] | None = None) -> str:
        """
        Create an optional negative prompt.

        TODO: Derive quality / artifact constraints from product category.
        """
        logger.debug("prompt_builder_service.build_negative_prompt called")
        raise NotImplementedError("Negative prompt building is not implemented in Version 1")


def get_prompt_builder_service() -> PromptBuilderService:
    """FastAPI dependency factory for PromptBuilderService."""
    return PromptBuilderService()
