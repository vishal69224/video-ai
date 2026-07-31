"""Image upload endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.logger import get_logger
from app.schemas.upload_schema import UploadResponse
from app.services.upload_service import UploadService, get_upload_service

router = APIRouter(prefix="/api", tags=["Upload"])
logger = get_logger()


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload reference images",
    description="Accept 1–10 JPG/JPEG/PNG/WEBP images (max 20 MB each).",
)
async def upload_images(
    files: list[UploadFile] = File(..., description="One to ten image files"),
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    """Validate and store uploaded reference images."""
    logger.info("POST /api/upload received {} file(s)", len(files))
    response = await upload_service.upload_images(files)
    logger.info("POST /api/upload completed with {} stored file(s)", len(response.files))
    return response
