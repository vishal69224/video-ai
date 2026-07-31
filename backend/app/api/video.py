"""Video generation endpoints (placeholders for future Kie.ai integration)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logger import get_logger
from app.schemas.response_schema import VideoGenerateRequest, VideoGenerateResponse
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/api", tags=["Video"])
logger = get_logger()


@router.post(
    "/video/generate",
    response_model=VideoGenerateResponse,
    summary="Generate AI video (not implemented)",
    description="Placeholder endpoint for future cinematic video generation.",
)
async def generate_video(
    payload: VideoGenerateRequest,
    task_service: TaskService = Depends(get_task_service),
) -> VideoGenerateResponse:
    """
    Kick off a video generation task.

    TODO: Wire to TaskService once analysis + Kie.ai are implemented.
    """
    logger.info("POST /api/video/generate called with {} references", len(payload.file_urls))
    try:
        result = await task_service.create_generation_task(
            file_urls=payload.file_urls,
            project_name=payload.project_name,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc

    return VideoGenerateResponse(
        success=True,
        message="Video generation task created",
        task_id=result.get("task_id"),
    )
