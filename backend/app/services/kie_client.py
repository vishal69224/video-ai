"""Kie.ai HTTP client placeholders.

TODO: Integrate real Kie.ai video generation APIs with httpx.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logger import get_logger

logger = get_logger()


@dataclass
class KieClient:
    """Async client for future Kie.ai integration."""

    settings: Settings
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def startup(self) -> None:
        """Initialize the shared HTTP client."""
        # TODO: Configure auth headers using settings.KIE_API_KEY.
        self._client = httpx.AsyncClient(
            base_url=self.settings.KIE_BASE_URL or "https://example.invalid",
            timeout=httpx.Timeout(60.0),
        )
        logger.info("KieClient HTTP session created (placeholder)")

    async def shutdown(self) -> None:
        """Close the shared HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("KieClient HTTP session closed")

    async def create_video_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Submit a video generation task.

        TODO: POST to Kie.ai create-task endpoint.
        TODO: Map internal prompt + reference images to provider schema.
        """
        logger.debug("kie_client.create_video_task called")
        raise NotImplementedError("Kie.ai video creation is not implemented in Version 1")

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Fetch generation task status.

        TODO: GET task status from Kie.ai.
        TODO: Normalize provider statuses into internal enums.
        """
        logger.debug("kie_client.get_task_status called task_id={}", task_id)
        raise NotImplementedError("Kie.ai status polling is not implemented in Version 1")


def get_kie_client() -> KieClient:
    """FastAPI dependency factory for KieClient."""
    return KieClient(settings=get_settings())
