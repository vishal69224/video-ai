"""Health and task-status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.schemas.response_schema import StatusResponse
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/api", tags=["Status"])
logger = get_logger()


@router.get(
    "/health",
    response_model=StatusResponse,
    summary="Health check",
)
async def health_check(settings: Settings = Depends(get_settings)) -> StatusResponse:
    """Return basic application health information."""
    return StatusResponse(
        success=True,
        message="Backend is healthy",
        data={
            "app_name": settings.APP_NAME,
            "debug": settings.DEBUG,
        },
    )


@router.get(
    "/status/{task_id}",
    response_model=StatusResponse,
    summary="Get generation task status (not implemented)",
)
async def get_task_status(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
) -> StatusResponse:
    """
    Poll a generation task by ID.

    TODO: Return normalized provider status once TaskService is implemented.
    """
    logger.info("GET /api/status/{} called", task_id)
    try:
        task = await task_service.get_task(task_id)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc

    return StatusResponse(
        success=True,
        message="Task status retrieved",
        data=task,
    )
