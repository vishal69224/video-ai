"""Schemas related to image uploads."""

from pydantic import BaseModel, Field


class UploadedFileInfo(BaseModel):
    """Metadata for a single uploaded image."""

    filename: str = Field(..., description="Stored unique filename")
    url: str = Field(..., description="Public URL path for the uploaded file")
    original_filename: str | None = Field(
        default=None,
        description="Original client filename before uniquification",
    )
    size: int | None = Field(default=None, description="File size in bytes")
    content_type: str | None = Field(default=None, description="Detected content type")


class UploadResponse(BaseModel):
    """Successful multi-image upload response."""

    success: bool = True
    message: str = "Images uploaded successfully"
    files: list[UploadedFileInfo]
