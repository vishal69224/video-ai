"""Image-to-video prompt generation endpoints."""

from fastapi import APIRouter, Depends

from app.core.exceptions import ImagePromptGenerationError, VideoGenerationError
from app.core.logger import get_logger
from app.schemas.prompt_schema import (
    PromptGenerateRequest,
    PromptGenerateResponse,
    PromptPreviewRequest,
    PromptPreviewResponse,
)
from app.services.image_prompt_service import ImagePromptService, get_image_prompt_service
from app.services.video_generation_service import (
    VideoGenerationService,
    get_video_generation_service,
)

router = APIRouter(prefix="/api", tags=["Prompt"])
logger = get_logger()


@router.post(
    "/prompt/generate",
    response_model=PromptGenerateResponse,
    summary="Generate cinematic image-to-video prompt",
    description=(
        "Analyze one or more uploaded reference images with local Gemma 3 (Ollama) "
        "and return a single Kie.ai-ready prompt. Does not call Kie.ai."
    ),
)
async def generate_prompt(
    payload: PromptGenerateRequest,
    prompt_service: ImagePromptService = Depends(get_image_prompt_service),
) -> PromptGenerateResponse:
    """Generate a professional image-to-video prompt from uploaded images."""
    logger.info(
        "POST /api/prompt/generate received {} image path(s)",
        len(payload.image_paths),
    )

    try:
        prompt = await prompt_service.generate_prompt(
            payload.image_paths,
            model=payload.api_model,
            duration_seconds=payload.duration_seconds,
            resolution=payload.resolution,
        )
    except ImagePromptGenerationError:
        raise

    logger.info("POST /api/prompt/generate completed successfully")
    return PromptGenerateResponse(success=True, prompt=prompt)


@router.post(
    "/prompt/preview",
    response_model=PromptPreviewResponse,
    summary="Credit-safe prompt preview",
    description=(
        "Generate a fashion-commercial prompt with Gemma, estimate credits, and run "
        "validation checks. Never calls Kie.ai and never consumes credits."
    ),
)
async def preview_prompt(
    payload: PromptPreviewRequest,
    video_service: VideoGenerationService = Depends(get_video_generation_service),
) -> PromptPreviewResponse:
    """Return generated prompt + estimates + validation without calling Kie.ai."""
    logger.info(
        "POST /api/prompt/preview received {} image path(s) — Development Mode preview",
        len(payload.image_paths),
    )
    try:
        result = await video_service.preview_prompt(
            payload.image_paths,
            api_model=payload.api_model,
            resolution=payload.resolution,
            duration_seconds=payload.duration_seconds,
            estimated_credits=payload.estimated_credits,
        )
    except ImagePromptGenerationError as exc:
        raise VideoGenerationError(exc.message, code=exc.code) from exc

    logger.info("POST /api/prompt/preview completed (Kie.ai not called)")
    return PromptPreviewResponse(**result)
