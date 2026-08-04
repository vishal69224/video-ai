"""Schemas for image-to-video prompt generation."""

from typing import Any

from pydantic import BaseModel, Field


class PromptGenerateRequest(BaseModel):
    """Request body for generating a cinematic prompt from uploaded images."""

    image_paths: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of uploaded image paths or /uploads/... URLs",
        examples=[
            [
                "/uploads/front.png",
                "/uploads/back.png",
                "/uploads/side.png",
            ]
        ],
    )
    api_model: str | None = Field(
        default=None,
        description="Optional Kie model slug for provider-aware prompt optimization",
    )
    resolution: str | None = Field(default=None)
    duration_seconds: int | None = Field(default=None)


class PromptGenerateResponse(BaseModel):
    """Successful prompt generation response."""

    success: bool = True
    prompt: str


class PromptPreviewRequest(BaseModel):
    """Request body for credit-safe prompt preview (no Kie.ai call)."""

    image_paths: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Uploaded image paths or /uploads/... URLs",
    )
    project_name: str | None = Field(default=None)
    model_id: str | None = Field(default=None)
    api_model: str | None = Field(default=None)
    resolution: str | None = Field(default=None)
    duration_seconds: int | None = Field(default=None)
    estimated_credits: float | None = Field(default=None)


class PromptPreviewResponse(BaseModel):
    """Prompt preview + validation results. Never calls Kie.ai."""

    success: bool = True
    development_mode: bool = True
    generated_prompt: str
    estimated_model: str
    estimated_resolution: str
    estimated_duration: str
    estimated_credits: float
    validation: dict[str, Any]
    message: str = "Prompt preview completed. Kie.ai was not called."
