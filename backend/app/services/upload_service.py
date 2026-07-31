"""Upload service — validation, unique naming, and persistence."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import UploadFile

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.schemas.upload_schema import UploadedFileInfo, UploadResponse
from app.utils.file_utils import ensure_directory, generate_unique_filename, save_bytes
from app.utils.image_utils import build_upload_url
from app.utils.validators import (
    ensure_unique_original_names,
    validate_image_file,
    validate_upload_count,
)

logger = get_logger()


@dataclass
class UploadService:
    """Handles image upload workflows."""

    settings: Settings

    async def upload_images(self, files: list[UploadFile]) -> UploadResponse:
        """Validate and store 1–10 reference images."""
        validate_upload_count(len(files), self.settings)

        original_names = [file.filename or f"unnamed-{index}" for index, file in enumerate(files)]
        ensure_unique_original_names(original_names)

        upload_dir = await ensure_directory(self.settings.upload_path)
        stored: list[UploadedFileInfo] = []

        for file in files:
            extension, content = await validate_image_file(file, self.settings)
            unique_name = generate_unique_filename(file.filename or f"image.{extension}")
            destination = upload_dir / unique_name
            await save_bytes(destination, content)

            info = UploadedFileInfo(
                filename=unique_name,
                url=build_upload_url(unique_name),
                original_filename=file.filename,
                size=len(content),
                content_type=file.content_type,
            )
            stored.append(info)
            logger.info(
                "Upload accepted original='{}' stored='{}' size={}",
                file.filename,
                unique_name,
                len(content),
            )

        return UploadResponse(
            success=True,
            message="Images uploaded successfully",
            files=stored,
        )


def get_upload_service() -> UploadService:
    """FastAPI dependency factory for UploadService."""
    return UploadService(settings=get_settings())
