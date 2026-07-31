"""Shared API response envelopes."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error payload returned by exception handlers."""

    success: bool = False
    message: str
    detail: Any | None = None


class StatusResponse(BaseModel):
    """Generic health / status payload."""

    success: bool = True
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class VideoGenerateRequest(BaseModel):
    """
    Placeholder request body for future video generation.

    TODO: Expand with prompt overrides, aspect ratio, and duration options.
    """

    file_urls: list[str] = Field(
        default_factory=list,
        description="Uploaded image URLs to use as references",
    )
    project_name: str | None = Field(default=None, description="Optional project title")


class VideoGenerateResponse(BaseModel):
    """Placeholder response for future video generation."""

    success: bool = True
    message: str
    task_id: str | None = None
