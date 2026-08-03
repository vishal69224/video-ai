"""Library service — MongoDB-backed completed video metadata."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends

from app.core.exceptions import VideoGenerationError
from app.core.logger import get_logger
from app.models.video_model import VideoDocument, VideoDocumentCreate
from app.repositories.video_repository import VideoRepository, get_video_repository
from app.schemas.video_schema import (
    DeleteVideoResponse,
    LibraryListResponse,
    LibraryVideoItem,
)
from app.services.video_store import VideoTaskRecord, video_store

logger = get_logger()


class VideoLibraryService:
    """Application service for listing, fetching, deleting, and persisting videos."""

    def __init__(self, repository: VideoRepository) -> None:
        self._repository = repository

    async def save_completed_from_task(
        self,
        record: VideoTaskRecord,
        *,
        credits_used: int | None = None,
        model: str | None = None,
    ) -> VideoDocument | None:
        """
        Persist metadata only after a successful generation with a valid video_url.

        Failed generations are ignored (no completed MongoDB record).
        """
        video_url = (record.video_url or "").strip()
        if record.status != "completed" or not video_url:
            logger.info(
                "Skip MongoDB persist task_id={} status={} has_url={}",
                record.task_id,
                record.status,
                bool(video_url),
            )
            return None

        created_at = self._parse_datetime(record.created_at)
        payload = VideoDocumentCreate(
            task_id=record.task_id,
            project_name=(record.title or "").strip() or "Product Film",
            prompt=record.prompt or "",
            thumbnail_url=record.thumbnail_url,
            video_url=video_url,
            status="completed",
            model=model or getattr(record, "model", None),
            resolution=record.resolution,
            duration=record.duration,
            credits_used=(
                credits_used
                if credits_used is not None
                else getattr(record, "credits_used", None)
            ),
            created_at=created_at,
            updated_at=datetime.now(timezone.utc),
        )

        document = await self._repository.upsert_completed(
            payload,
            document_id=record.id,
        )
        logger.info(
            "Saved completed video to MongoDB id={} task_id={}",
            document.id,
            document.task_id,
        )
        return document

    async def list_videos(self, search: str | None = None) -> LibraryListResponse:
        """Return completed videos from MongoDB, newest first."""
        documents = await self._repository.list_videos(search=search)
        return LibraryListResponse(
            success=True,
            videos=[self._to_library_item(item) for item in documents],
        )

    async def get_video(self, video_id: str) -> LibraryVideoItem:
        """Return one completed video by id."""
        document = await self._repository.get_by_id(video_id)
        if document is None:
            raise VideoGenerationError(
                f"Video not found: {video_id}",
                code="video_not_found",
            )
        return self._to_library_item(document)

    async def delete_video(self, video_id: str) -> DeleteVideoResponse:
        """Delete MongoDB metadata (does not delete remote Kie assets)."""
        deleted = await self._repository.delete_by_id(video_id)
        # Best-effort cleanup of any in-memory twin.
        video_store.delete(video_id)
        if not deleted:
            raise VideoGenerationError(
                f"Video not found: {video_id}",
                code="video_not_found",
            )
        return DeleteVideoResponse(success=True, message="Video deleted successfully.")

    @staticmethod
    def _to_library_item(document: VideoDocument) -> LibraryVideoItem:
        created = document.created_at
        created_at = (
            created.isoformat()
            if isinstance(created, datetime)
            else str(created)
        )
        return LibraryVideoItem(
            id=document.id,
            title=document.project_name,
            created_at=created_at,
            duration=document.duration or "0:05",
            resolution=document.resolution or "1080 × 1920",
            thumbnail=document.thumbnail_url,
            thumbnail_url=document.thumbnail_url,
            video_url=document.video_url,
            prompt=document.prompt,
            status=document.status,
            task_id=document.task_id,
            model=document.model,
            credits_used=document.credits_used,
        )

    @staticmethod
    def _parse_datetime(value: str | datetime | None) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)


def get_video_library_service(
    repository: VideoRepository = Depends(get_video_repository),
) -> VideoLibraryService:
    """FastAPI dependency for VideoLibraryService."""
    return VideoLibraryService(repository=repository)
