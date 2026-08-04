"""Abstract vision provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseVisionProvider(ABC):
    """
    Common interface for image-analysis providers.

    Implementations must accept 1–10 image references and return raw text
    (typically structured JSON for fashion analysis).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short provider identifier (e.g. openrouter, ollama)."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model slug used for requests."""

    @abstractmethod
    async def analyze_images(
        self,
        image_urls: list[str],
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
    ) -> str:
        """
        Analyze one or more images and return the model text response.

        Args:
            image_urls: Local filesystem paths and/or http(s)/data URLs.
            system_prompt: System instruction.
            user_prompt: User instruction.
            temperature: Sampling temperature for the provider.
        """
