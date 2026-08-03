"""Health and account endpoints."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.schemas.response_schema import CreditsResponse, StatusResponse
from app.services.kie_client import KieClient, get_kie_client

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
            "development_mode": bool(settings.DEVELOPMENT_MODE),
            "kie_configured": bool(settings.KIE_API_KEY.strip()),
        },
    )


@router.get(
    "/credits",
    response_model=CreditsResponse,
    summary="Get Kie.ai credit balance",
)
async def get_credits(
    kie_client: KieClient = Depends(get_kie_client),
) -> CreditsResponse:
    """Return the current remaining Kie.ai account credits."""
    logger.info("GET /api/credits called")
    credits = await kie_client.get_credits()
    return CreditsResponse(
        success=True,
        credits=credits,
        message="Credits retrieved successfully.",
    )
