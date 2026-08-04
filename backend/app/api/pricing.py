"""Serve the single Seedance pricing catalog to the frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.logger import get_logger
from app.schemas.response_schema import StatusResponse
from app.services.seedance_pricing_engine import (
    SeedancePricingEngine,
    get_seedance_pricing_engine,
)

router = APIRouter(prefix="/api/pricing", tags=["Pricing"])
logger = get_logger()


@router.get(
    "",
    response_model=StatusResponse,
    summary="Get Seedance pricing catalog (credits_per_second)",
)
async def get_pricing_catalog(
    ui_only: bool = Query(default=True, description="Only return UI-visible models"),
    engine: SeedancePricingEngine = Depends(get_seedance_pricing_engine),
) -> StatusResponse:
    catalog = engine.get_catalog(ui_only=ui_only)
    logger.info("GET /api/pricing models={}", len(catalog.get("models") or []))
    return StatusResponse(
        success=True,
        message="Pricing catalog loaded.",
        data=catalog,
    )
