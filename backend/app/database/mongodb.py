"""MongoDB connection helpers (Motor async)."""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.logger import get_logger

logger = get_logger()

_client: AsyncIOMotorClient[Any] | None = None
_database: AsyncIOMotorDatabase[Any] | None = None


async def init_mongodb(settings: Settings | None = None) -> AsyncIOMotorDatabase[Any]:
    """Create the shared Motor client and verify connectivity."""
    global _client, _database

    runtime = settings or get_settings()
    uri = runtime.MONGODB_URI.strip()
    db_name = runtime.MONGODB_DB.strip() or "video_ai"

    if not uri:
        raise RuntimeError("MONGODB_URI is not configured")

    if _client is not None and _database is not None:
        return _database

    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=5_000,
        uuidRepresentation="standard",
    )
    await client.admin.command("ping")
    database = client[db_name]

    _client = client
    _database = database
    logger.info("MongoDB connected database='{}'", db_name)
    return database


async def close_mongodb() -> None:
    """Close the shared Motor client."""
    global _client, _database
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase[Any]:
    """Return the initialized database or raise if unavailable."""
    if _database is None:
        raise RuntimeError("MongoDB is not initialized. Call init_mongodb() on startup.")
    return _database
