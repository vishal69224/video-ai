"""Filesystem helpers for uploads and generated assets."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
import aiofiles.os

from app.core.logger import get_logger

logger = get_logger()


async def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not exist."""
    await aiofiles.os.makedirs(path, exist_ok=True)
    return path


def generate_unique_filename(original_filename: str) -> str:
    """Generate a collision-resistant filename preserving the original extension."""
    extension = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{extension}"


async def save_bytes(path: Path, data: bytes) -> Path:
    """Persist binary content asynchronously."""
    await ensure_directory(path.parent)
    async with aiofiles.open(path, "wb") as file:
        await file.write(data)
    logger.info("Saved file: {}", path)
    return path


async def delete_file(path: Path) -> bool:
    """Delete a file if it exists. Returns True when removed."""
    try:
        await aiofiles.os.remove(path)
        logger.info("Deleted file: {}", path)
        return True
    except FileNotFoundError:
        logger.warning("File not found for deletion: {}", path)
        return False
