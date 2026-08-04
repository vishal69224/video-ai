"""Selects and invokes the configured vision AI provider."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends

from app.ai.providers.base_provider import BaseVisionProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.core.config import Settings, get_settings
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger

logger = get_logger()


@dataclass
class AIOrchestrator:
    """
    Provider-agnostic entry point for vision analysis.

    ImagePromptService talks only to this orchestrator — never to a
    concrete provider (OpenRouter, Ollama, etc.).
    """

    settings: Settings
    provider: BaseVisionProvider

    async def analyze_images(
        self,
        image_paths: list[Path | str],
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
    ) -> str:
        """
        Analyze images with the selected provider.

        Returns:
            Raw model text (expected to be fashion-analysis JSON).
        """
        if not image_paths:
            raise ImagePromptGenerationError(
                "At least one image path is required",
                code="invalid_image",
            )

        image_urls = [str(path) for path in image_paths]
        logger.info(
            "AI orchestrator provider={} model={} images={}",
            self.provider.name,
            self.provider.model,
            len(image_urls),
        )
        return await self.provider.analyze_images(
            image_urls,
            system_prompt,
            user_prompt,
            temperature=temperature,
        )


def build_vision_provider(settings: Settings) -> BaseVisionProvider:
    """Factory for the configured vision provider."""
    provider_name = (settings.AI_PROVIDER or "openrouter").strip().lower()
    if provider_name in {"openrouter", "open-router"}:
        return OpenRouterProvider(settings=settings)
    if provider_name == "ollama":
        return OllamaProvider(settings=settings)
    raise ImagePromptGenerationError(
        f"Unsupported AI_PROVIDER '{settings.AI_PROVIDER}'. "
        "Use 'openrouter' or 'ollama'.",
        code="prompt_generation_failed",
    )


def get_ai_orchestrator(
    settings: Settings = Depends(get_settings),
) -> AIOrchestrator:
    """FastAPI dependency factory for AIOrchestrator."""
    provider = build_vision_provider(settings)
    return AIOrchestrator(settings=settings, provider=provider)
