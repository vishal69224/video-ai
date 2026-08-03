"""Schemas for video generation orchestration."""

from pydantic import BaseModel, Field


class VideoGenerationRequest(BaseModel):
    """Request body for starting image-to-video generation."""

    image_paths: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Uploaded image paths or /uploads/... URLs",
    )
    project_name: str | None = Field(default=None, description="Optional library title")
    model_id: str | None = Field(default=None, description="Frontend model catalog id")
    api_model: str | None = Field(default=None, description="Provider model slug")
    resolution: str | None = Field(default=None, description="Requested output resolution")
    duration_seconds: int | None = Field(default=None, description="Requested clip duration")
    estimated_credits: int | None = Field(default=None, description="Client-side credit estimate")


class VideoGenerationResponse(BaseModel):
    """Successful video generation start response (production or development)."""

    success: bool = True
    status: str = "processing"
    task_id: str | None = None
    prompt: str | None = None
    message: str = "Video generation started successfully."

    # Credit-safe development mode fields (populated only when DEVELOPMENT_MODE=true).
    development_mode: bool = False
    generated_prompt: str | None = None
    estimated_model: str | None = None
    estimated_resolution: str | None = None
    estimated_duration: str | None = None
    estimated_credits: int | None = None


class VideoStatusResponse(BaseModel):
    """Polled generation status response."""

    success: bool = True
    task_id: str
    status: str
    stage: str
    progress: int = 0
    prompt: str | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    created_at: str | None = None
    duration: str | None = None
    resolution: str | None = None
    title: str | None = None
    message: str | None = None
    error_message: str | None = None


class LibraryVideoItem(BaseModel):
    """Library card payload."""

    id: str
    title: str
    created_at: str
    duration: str
    resolution: str
    thumbnail: str | None = None
    thumbnail_url: str | None = None
    video_url: str | None = None
    prompt: str
    status: str
    task_id: str
    model: str | None = None
    credits_used: int | None = None


class LibraryListResponse(BaseModel):
    """List of generated videos."""

    success: bool = True
    videos: list[LibraryVideoItem]


class DeleteVideoResponse(BaseModel):
    """Delete confirmation payload."""

    success: bool = True
    message: str = "Video deleted successfully."
