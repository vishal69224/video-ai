"""Ollama local vision provider."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from ollama import ResponseError, chat

from app.ai.providers.base_provider import BaseVisionProvider
from app.core.config import Settings
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger

logger = get_logger()


@dataclass
class OllamaProvider(BaseVisionProvider):
    """Vision analysis via a local Ollama server."""

    settings: Settings

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self.settings.OLLAMA_MODEL

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

        local_paths = [self._to_local_path(url) for url in image_urls]
        started = time.perf_counter()
        logger.info(
            "AI request provider={} model={} images={}",
            self.name,
            self.model,
            len(local_paths),
        )

        try:
            content = await asyncio.to_thread(
                self._chat,
                local_paths,
                system_prompt,
                user_prompt,
                temperature,
            )
        except ResponseError as exc:
            message = str(exc).lower()
            if "not found" in message or "pull" in message:
                raise ImagePromptGenerationError(
                    f"Ollama model '{self.model}' is missing. "
                    f"Run: ollama pull {self.model}",
                    code="model_missing",
                ) from exc
            if "failed to load image" in message or "invalid_request_error" in message:
                raise ImagePromptGenerationError(
                    f"Invalid image for vision model: {exc}",
                    code="invalid_image",
                ) from exc
            raise ImagePromptGenerationError(
                f"Ollama request failed: {exc}",
                code="ollama_unavailable",
            ) from exc
        except ConnectionError as exc:
            raise ImagePromptGenerationError(
                "Ollama is unavailable. Ensure the Ollama server is running.",
                code="ollama_unavailable",
            ) from exc
        except OSError as exc:
            raise ImagePromptGenerationError(
                f"Ollama is unavailable: {exc}",
                code="ollama_unavailable",
            ) from exc

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "AI response provider={} model={} images={} duration_ms={:.1f} "
            "response_length={}",
            self.name,
            self.model,
            len(local_paths),
            duration_ms,
            len(content or ""),
        )
        return content

    def _chat(
        self,
        image_paths: list[Path],
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        previous_host = os.environ.get("OLLAMA_HOST")
        os.environ["OLLAMA_HOST"] = self.settings.OLLAMA_HOST
        try:
            response = chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": user_prompt,
                        "images": [str(path) for path in image_paths],
                    },
                ],
                format="json",
                options={"temperature": temperature, "num_predict": 700},
            )
        finally:
            if previous_host is None:
                os.environ.pop("OLLAMA_HOST", None)
            else:
                os.environ["OLLAMA_HOST"] = previous_host

        message = getattr(response, "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if content is None and isinstance(response, dict):
            content = response.get("message", {}).get("content")
        return str(content or "").strip()

    @staticmethod
    def _to_local_path(image_ref: str) -> Path:
        raw = (image_ref or "").strip()
        if not raw:
            raise ImagePromptGenerationError("Empty image path", code="invalid_image")

        if raw.startswith("file://"):
            parsed = urlparse(raw)
            raw = unquote(parsed.path)

        path = Path(raw).expanduser()
        if not path.is_file():
            raise ImagePromptGenerationError(
                f"Image file not found: {image_ref}",
                code="invalid_image",
            )
        return path.resolve()
