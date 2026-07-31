"""Task orchestration placeholders.

TODO: Coordinate analysis → prompt → Kie.ai generation → status polling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logger import get_logger
from app.services.image_analysis_service import ImageAnalysisService, get_image_analysis_service
from app.services.kie_client import KieClient, get_kie_client
from app.services.prompt_builder_service import PromptBuilderService, get_prompt_builder_service

logger = get_logger()


@dataclass
class TaskService:
    """Orchestrates end-to-end video generation workflows."""

    analysis_service: ImageAnalysisService
    prompt_service: PromptBuilderService
    kie_client: KieClient

    async def create_generation_task(
        self,
        file_urls: list[str],
        project_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new video generation task.

        TODO: Resolve file URLs to local paths.
        TODO: Run image analysis.
        TODO: Build cinematic prompt.
        TODO: Submit task via KieClient.
        TODO: Persist in-memory / future store task metadata.
        """
        logger.debug(
            "task_service.create_generation_task urls={} project_name={}",
            len(file_urls),
            project_name,
        )
        raise NotImplementedError("Task creation is not implemented in Version 1")

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """
        Retrieve task state for status polling.

        TODO: Load task metadata.
        TODO: Optionally refresh remote provider status.
        """
        logger.debug("task_service.get_task called task_id={}", task_id)
        raise NotImplementedError("Task retrieval is not implemented in Version 1")


def get_task_service() -> TaskService:
    """FastAPI dependency factory for TaskService."""
    return TaskService(
        analysis_service=get_image_analysis_service(),
        prompt_service=get_prompt_builder_service(),
        kie_client=get_kie_client(),
    )
