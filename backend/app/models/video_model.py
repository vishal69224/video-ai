"""Pydantic models for persisted video metadata (no binary MP4 data)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VideoDocumentCreate(BaseModel):
    """Payload used when inserting/upserting a completed video."""

    task_id: str
    project_name: str = "Product Film"
    prompt: str = ""
    thumbnail_url: str | None = None
    video_url: str
    status: str = "completed"
    model: str | None = None
    resolution: str | None = None
    duration: str | None = None
    credits_used: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class VideoDocument(VideoDocumentCreate):
    """Full video metadata document returned from MongoDB."""

    id: str = Field(..., description="MongoDB document id")

    @classmethod
    def from_mongo(cls, document: dict[str, Any]) -> VideoDocument:
        """Map a raw MongoDB document into a typed model."""
        payload = dict(document)
        raw_id = payload.pop("_id", None)
        return cls(id=str(raw_id), **payload)
