"""Validation helpers for uploaded image files."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings

CONTENT_TYPE_MAP: dict[str, set[str]] = {
    "jpg": {"image/jpeg", "image/jpg"},
    "jpeg": {"image/jpeg", "image/jpg"},
    "png": {"image/png"},
    "webp": {"image/webp"},
}


def get_extension(filename: str | None) -> str:
    """Return the lowercase file extension without a leading dot."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def validate_extension(filename: str | None, settings: Settings) -> str:
    """Validate that the filename uses an allowed image extension."""
    extension = get_extension(filename)
    if extension not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{extension or 'unknown'}'. Allowed: {allowed}",
        )
    return extension


def validate_content_type(content_type: str | None, extension: str) -> None:
    """Validate Content-Type against the declared extension when provided."""
    if not content_type:
        return
    allowed_types = CONTENT_TYPE_MAP.get(extension, set())
    normalized = content_type.split(";")[0].strip().lower()
    if allowed_types and normalized not in allowed_types and normalized != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type '{normalized}' does not match extension '.{extension}'",
        )


def validate_file_size(size: int, settings: Settings) -> None:
    """Validate uploaded file size against configured limits."""
    if size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty files are not allowed",
        )
    if size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {max_mb:.0f} MB",
        )


def validate_upload_count(count: int, settings: Settings) -> None:
    """Validate the number of uploaded files."""
    if count < settings.MIN_UPLOAD_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {settings.MIN_UPLOAD_COUNT} image is required",
        )
    if count > settings.MAX_UPLOAD_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A maximum of {settings.MAX_UPLOAD_COUNT} images is allowed",
        )


async def validate_image_file(file: UploadFile, settings: Settings) -> tuple[str, bytes]:
    """
    Validate an UploadFile and return (extension, content bytes).

    Checks extension, content type, emptiness, and size.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each file must include a filename",
        )

    extension = validate_extension(file.filename, settings)
    validate_content_type(file.content_type, extension)

    content = await file.read()
    validate_file_size(len(content), settings)
    await file.seek(0)

    return extension, content


def ensure_unique_original_names(filenames: list[str]) -> None:
    """Reject batches that contain duplicate original filenames."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in filenames:
        key = name.lower()
        if key in seen:
            duplicates.add(name)
        seen.add(key)

    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate filenames are not allowed: {joined}",
        )
