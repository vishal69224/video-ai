"""MongoDB repository for completed video metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.core.logger import get_logger
from app.database.mongodb import get_database
from app.models.video_model import VideoDocument, VideoDocumentCreate

logger = get_logger()

COLLECTION_NAME = "videos"


class VideoRepository:
    """Reusable async data-access layer for video metadata."""

    def __init__(self, database: AsyncIOMotorDatabase[Any]) -> None:
        self._db = database
        self._collection: AsyncIOMotorCollection[Any] = database[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        """Create required indexes (idempotent)."""
        await self._collection.create_index("task_id", unique=True, name="uniq_task_id")
        await self._collection.create_index([("created_at", DESCENDING)], name="created_at_desc")
        await self._collection.create_index("status", name="status_idx")
        await self._collection.create_index(
            [("project_name", ASCENDING), ("model", ASCENDING)],
            name="project_model_idx",
        )
        logger.info("MongoDB indexes ensured for collection='{}'", COLLECTION_NAME)

    async def upsert_completed(
        self,
        payload: VideoDocumentCreate,
        *,
        document_id: str | None = None,
    ) -> VideoDocument:
        """
        Insert or update a completed video by task_id.

        Only call this when video_url is a valid non-empty URL.
        """
        video_url = (payload.video_url or "").strip()
        if not video_url:
            raise ValueError("video_url is required to persist a completed video")

        now = datetime.now(timezone.utc)
        set_fields = payload.model_dump(exclude={"created_at"})
        set_fields["video_url"] = video_url
        set_fields["status"] = "completed"
        set_fields["updated_at"] = now

        # Preserve original created_at / _id on inserts only.
        set_on_insert: dict[str, Any] = {
            "created_at": payload.created_at or now,
        }
        if document_id:
            try:
                set_on_insert["_id"] = ObjectId(document_id)
            except InvalidId:
                set_on_insert["_id"] = document_id

        try:
            await self._collection.update_one(
                {"task_id": payload.task_id},
                {"$set": set_fields, "$setOnInsert": set_on_insert},
                upsert=True,
            )
        except DuplicateKeyError:
            # Race on unique task_id — fall back to plain update.
            await self._collection.update_one(
                {"task_id": payload.task_id},
                {"$set": set_fields},
            )

        document = await self._collection.find_one({"task_id": payload.task_id})
        if document is None:
            raise RuntimeError(f"Failed to persist video task_id={payload.task_id}")
        return VideoDocument.from_mongo(document)

    async def list_videos(
        self,
        *,
        search: str | None = None,
        limit: int = 200,
    ) -> list[VideoDocument]:
        """Return videos newest-first, optionally filtered by project/prompt/model."""
        query: dict[str, Any] = {"status": "completed"}
        term = (search or "").strip()
        if term:
            regex = {"$regex": term, "$options": "i"}
            query["$or"] = [
                {"project_name": regex},
                {"prompt": regex},
                {"model": regex},
            ]

        cursor = (
            self._collection.find(query)
            .sort("created_at", DESCENDING)
            .limit(max(1, min(limit, 500)))
        )
        documents = await cursor.to_list(length=max(1, min(limit, 500)))
        return [VideoDocument.from_mongo(item) for item in documents]

    async def get_by_id(self, video_id: str) -> VideoDocument | None:
        """Fetch one video by MongoDB id."""
        query = self._id_query(video_id)
        if query is None:
            return None
        document = await self._collection.find_one(query)
        return VideoDocument.from_mongo(document) if document else None

    async def get_by_task_id(self, task_id: str) -> VideoDocument | None:
        """Fetch one video by Kie task id."""
        document = await self._collection.find_one({"task_id": task_id})
        return VideoDocument.from_mongo(document) if document else None

    async def delete_by_id(self, video_id: str) -> bool:
        """Delete metadata by id. Returns True when a document was removed."""
        query = self._id_query(video_id)
        if query is None:
            return False
        result = await self._collection.delete_one(query)
        return result.deleted_count > 0

    @staticmethod
    def _id_query(video_id: str) -> dict[str, Any] | None:
        value = (video_id or "").strip()
        if not value:
            return None
        try:
            return {"_id": ObjectId(value)}
        except InvalidId:
            return {"_id": value}


def get_video_repository() -> VideoRepository:
    """FastAPI dependency for VideoRepository."""
    return VideoRepository(get_database())
