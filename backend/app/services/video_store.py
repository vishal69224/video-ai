"""In-memory store for generation tasks and completed library videos."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VideoTaskRecord:
    """Persisted generation/library record."""

    id: str
    task_id: str
    status: str
    stage: str
    progress: int
    prompt: str
    title: str
    image_paths: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    video_url: str | None = None
    thumbnail_url: str | None = None
    duration: str = "0:05"
    resolution: str = "1080 × 1920"
    model: str | None = None
    credits_used: int | None = None
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VideoStore:
    """Thread-safe in-memory task/video registry."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, VideoTaskRecord] = {}
        self._by_task_id: dict[str, str] = {}

    def create(
        self,
        *,
        task_id: str,
        prompt: str,
        title: str,
        image_paths: list[str],
        image_urls: list[str],
        status: str = "processing",
        stage: str = "submitting_to_ai",
        progress: int = 40,
        thumbnail_url: str | None = None,
        duration: str = "0:05",
        resolution: str = "1080 × 1920",
        model: str | None = None,
        credits_used: int | None = None,
    ) -> VideoTaskRecord:
        record = VideoTaskRecord(
            id=str(uuid4()),
            task_id=task_id,
            status=status,
            stage=stage,
            progress=progress,
            prompt=prompt,
            title=title,
            image_paths=list(image_paths),
            image_urls=list(image_urls),
            thumbnail_url=thumbnail_url,
            duration=duration,
            resolution=resolution,
            model=model,
            credits_used=credits_used,
        )
        with self._lock:
            self._by_id[record.id] = record
            self._by_task_id[task_id] = record.id
        return deepcopy(record)

    def get_by_task_id(self, task_id: str) -> VideoTaskRecord | None:
        with self._lock:
            record_id = self._by_task_id.get(task_id)
            if not record_id:
                return None
            record = self._by_id.get(record_id)
            return deepcopy(record) if record else None

    def get_by_id(self, video_id: str) -> VideoTaskRecord | None:
        with self._lock:
            record = self._by_id.get(video_id)
            return deepcopy(record) if record else None

    def update(self, task_id: str, **changes: Any) -> VideoTaskRecord | None:
        with self._lock:
            record_id = self._by_task_id.get(task_id)
            if not record_id:
                return None
            record = self._by_id.get(record_id)
            if not record:
                return None
            for key, value in changes.items():
                if key == "task_id":
                    continue
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _utc_now()
            return deepcopy(record)

    def rebind_task_id(self, old_task_id: str, new_task_id: str, **changes: Any) -> VideoTaskRecord | None:
        """Replace a temporary task_id with the provider task_id."""
        with self._lock:
            record_id = self._by_task_id.get(old_task_id)
            if not record_id:
                return None
            record = self._by_id.get(record_id)
            if not record:
                return None
            self._by_task_id.pop(old_task_id, None)
            record.task_id = new_task_id
            for key, value in changes.items():
                if key == "task_id":
                    continue
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _utc_now()
            self._by_task_id[new_task_id] = record_id
            return deepcopy(record)

    def list_videos(self) -> list[VideoTaskRecord]:
        with self._lock:
            records = [deepcopy(item) for item in self._by_id.values()]
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records

    def delete(self, video_id: str) -> bool:
        with self._lock:
            record = self._by_id.pop(video_id, None)
            if not record:
                return False
            self._by_task_id.pop(record.task_id, None)
            return True


video_store = VideoStore()
