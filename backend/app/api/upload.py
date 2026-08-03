"""Image upload endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.logger import get_logger
from app.schemas.upload_schema import UploadResponse
from app.services.upload_service import UploadService, get_upload_service

router = APIRouter(prefix="/api", tags=["Upload"])
logger = get_logger()

UPLOAD_FILES_OPENAPI = {
    "type": "array",
    "title": "Files",
    "description": "One to ten image files (jpg, jpeg, png, webp)",
    "minItems": 1,
    "maxItems": 10,
    "items": {
        "type": "string",
        "format": "binary",
    },
}


def apply_upload_openapi_fix(openapi_schema: dict) -> None:
    """
    Ensure Swagger UI renders a native file picker for /api/upload.

    FastAPI/OpenAPI 3.1 emits contentMediaType for UploadFile arrays, which
    many Swagger UI builds still show as array<string>. Force format:binary.
    """
    body_schema_name = "Body_upload_images_api_upload_post"
    components = openapi_schema.setdefault("components", {}).setdefault("schemas", {})
    body_schema = components.get(body_schema_name)
    if isinstance(body_schema, dict):
        properties = body_schema.setdefault("properties", {})
        properties["files"] = dict(UPLOAD_FILES_OPENAPI)
        body_schema["required"] = ["files"]

    upload_path = openapi_schema.get("paths", {}).get("/api/upload", {}).get("post")
    if not upload_path:
        return

    upload_path["requestBody"] = {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["files"],
                    "properties": {
                        "files": dict(UPLOAD_FILES_OPENAPI),
                    },
                }
            }
        },
    }


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload reference images",
    description="Accept 1–10 JPG/JPEG/PNG/WEBP images (max 20 MB each).",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["files"],
                        "properties": {
                            "files": UPLOAD_FILES_OPENAPI,
                        },
                    }
                }
            },
        }
    },
)
async def upload_images(
    files: Annotated[
        list[UploadFile],
        File(
            description="One to ten image files (jpg, jpeg, png, webp)",
            media_type="image/jpeg,image/jpg,image/png,image/webp",
        ),
    ],
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    """Validate and store uploaded reference images."""
    logger.info("POST /api/upload received {} file(s)", len(files))
    response = await upload_service.upload_images(files)
    logger.info("POST /api/upload completed with {} stored file(s)", len(response.files))
    return response
