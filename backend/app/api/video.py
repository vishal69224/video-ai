"""Video generation, status, and library endpoints."""

from fastapi import APIRouter, Depends, Query

from app.core.logger import get_logger
from app.schemas.video_schema import (
    DeleteVideoResponse,
    LibraryListResponse,
    LibraryVideoItem,
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoStatusResponse,
)
from app.services.video_generation_service import (
    VideoGenerationService,
    get_video_generation_service,
)
from app.services.video_library_service import (
    VideoLibraryService,
    get_video_library_service,
)

router = APIRouter(prefix="/api", tags=["Video"])
logger = get_logger()


@router.post(
    "/video/generate",
    response_model=VideoGenerationResponse,
    summary="Generate AI video",
    description=(
        "Validate uploaded images, generate a Gemma cinematic prompt, "
        "submit a Kie.ai Image-to-Video job, and return task_id for polling."
    ),
)
async def generate_video(
    payload: VideoGenerationRequest,
    video_service: VideoGenerationService = Depends(get_video_generation_service),
) -> VideoGenerationResponse:
    """Start image-to-video generation and return the provider task_id."""
    logger.info(
        "POST /api/video/generate received {} image path(s)",
        len(payload.image_paths),
    )
    response = await video_service.generate(
        payload.image_paths,
        project_name=payload.project_name,
        model_id=payload.model_id,
        api_model=payload.api_model,
        resolution=payload.resolution,
        duration_seconds=payload.duration_seconds,
        estimated_credits=payload.estimated_credits,
    )
    logger.info(
        "POST /api/video/generate completed task_id={}",
        response.task_id,
    )
    return response


@router.get(
    "/video/status/{task_id}",
    response_model=VideoStatusResponse,
    summary="Poll video generation status",
)
async def get_video_status(
    task_id: str,
    video_service: VideoGenerationService = Depends(get_video_generation_service),
) -> VideoStatusResponse:
    """Return normalized generation status for a task."""
    logger.info("GET /api/video/status/{} called", task_id)
    return await video_service.get_status(task_id)


@router.get(
    "/videos",
    response_model=LibraryListResponse,
    summary="List generated videos",
)
async def list_videos(
    q: str | None = Query(
        default=None,
        description="Search by project name, prompt, or model",
    ),
    library_service: VideoLibraryService = Depends(get_video_library_service),
) -> LibraryListResponse:
    """Return completed videos from MongoDB, newest first."""
    logger.info("GET /api/videos called search={!r}", q)
    return await library_service.list_videos(search=q)


@router.get(
    "/videos/{video_id}",
    response_model=LibraryVideoItem,
    summary="Get one generated video",
)
async def get_video(
    video_id: str,
    library_service: VideoLibraryService = Depends(get_video_library_service),
) -> LibraryVideoItem:
    """Return one completed video metadata document."""
    logger.info("GET /api/videos/{} called", video_id)
    return await library_service.get_video(video_id)


@router.delete(
    "/videos/{video_id}",
    response_model=DeleteVideoResponse,
    summary="Delete a generated video",
)
async def delete_video(
    video_id: str,
    library_service: VideoLibraryService = Depends(get_video_library_service),
) -> DeleteVideoResponse:
    """Remove video metadata from MongoDB (does not delete remote Kie assets)."""
    logger.info("DELETE /api/videos/{} called", video_id)
    return await library_service.delete_video(video_id)
