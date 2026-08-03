"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import prompt as prompt_router
from app.api import status as status_router
from app.api import upload as upload_router
from app.api import video as video_router
from app.api.upload import apply_upload_openapi_fix
from app.core.config import get_settings, reload_settings
from app.core.exceptions import (
    ImagePromptGenerationError,
    KieGenerationError,
    VideoGenerationError,
)
from app.core.logger import configure_logging, get_logger
from app.database.mongodb import close_mongodb, init_mongodb
from app.repositories.video_repository import VideoRepository
from app.services.kie_client import KieClient
from app.utils.file_utils import ensure_directory

configure_logging()
logger = get_logger()
settings = reload_settings()

# Ensure mount targets exist at import time (StaticFiles requires existing dirs).
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.generated_path.mkdir(parents=True, exist_ok=True)
settings.static_path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    runtime_settings = reload_settings()
    app.state.settings = runtime_settings

    logger.info(
        "Starting {} on {}:{} kie_key={}",
        runtime_settings.APP_NAME,
        runtime_settings.HOST,
        runtime_settings.PORT,
        "set" if runtime_settings.KIE_API_KEY.strip() else "missing",
    )

    await ensure_directory(runtime_settings.upload_path)
    await ensure_directory(runtime_settings.generated_path)
    await ensure_directory(runtime_settings.static_path)

    kie_client = KieClient(settings=runtime_settings)
    await kie_client.startup()
    app.state.kie_client = kie_client

    database = await init_mongodb(runtime_settings)
    app.state.mongodb = database
    await VideoRepository(database).ensure_indexes()

    logger.info("Upload directory ready: {}", runtime_settings.upload_path)
    logger.info("Generated directory ready: {}", runtime_settings.generated_path)
    yield

    await kie_client.shutdown()
    await close_mongodb()
    logger.info("Shutting down {}", runtime_settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Video AI backend — upload, analyze, prompt, and generate cinematic videos.",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every inbound request and response status."""
    logger.info("→ {} {}", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error for {} {}", request.method, request.url.path)
        raise
    logger.info("← {} {} {}", request.method, request.url.path, response.status_code)
    return response


def _error_status_for_code(code: str) -> int:
    """Map internal error codes to HTTP status codes."""
    status_by_code = {
        "invalid_image": status.HTTP_400_BAD_REQUEST,
        "missing_images": status.HTTP_400_BAD_REQUEST,
        "validation_failed": status.HTTP_400_BAD_REQUEST,
        "empty_response": status.HTTP_502_BAD_GATEWAY,
        "model_missing": status.HTTP_503_SERVICE_UNAVAILABLE,
        "ollama_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
        "generation_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
        "prompt_generation_failed": status.HTTP_502_BAD_GATEWAY,
        "video_generation_failed": status.HTTP_502_BAD_GATEWAY,
        "kie_not_configured": status.HTTP_503_SERVICE_UNAVAILABLE,
        "kie_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
        "kie_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
        "kie_read_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
        "kie_connect_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
        "kie_write_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
        "kie_dns_failure": status.HTTP_503_SERVICE_UNAVAILABLE,
        "kie_unauthorized": status.HTTP_401_UNAUTHORIZED,
        "kie_rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
        "kie_server_error": status.HTTP_502_BAD_GATEWAY,
        "kie_request_rejected": status.HTTP_400_BAD_REQUEST,
        "kie_invalid_response": status.HTTP_502_BAD_GATEWAY,
        "kie_missing_task_id": status.HTTP_502_BAD_GATEWAY,
        "kie_file_upload_failed": status.HTTP_502_BAD_GATEWAY,
        "kie_polling_not_implemented": status.HTTP_501_NOT_IMPLEMENTED,
        "kie_generation_failed": status.HTTP_502_BAD_GATEWAY,
        "kie_task_not_found": status.HTTP_404_NOT_FOUND,
        "task_not_found": status.HTTP_404_NOT_FOUND,
        "video_not_found": status.HTTP_404_NOT_FOUND,
    }
    return status_by_code.get(code, status.HTTP_502_BAD_GATEWAY)


@app.exception_handler(ImagePromptGenerationError)
async def image_prompt_exception_handler(
    _: Request,
    exc: ImagePromptGenerationError,
) -> JSONResponse:
    """Map prompt-generation failures to structured HTTP errors."""
    status_code = _error_status_for_code(exc.code)
    logger.warning("ImagePromptGenerationError code={} message={}", exc.code, exc.message)
    return ORJSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": exc.message,
            "detail": {"code": exc.code},
        },
    )


@app.exception_handler(VideoGenerationError)
async def video_generation_exception_handler(
    _: Request,
    exc: VideoGenerationError,
) -> JSONResponse:
    """Map video orchestration failures to structured HTTP errors."""
    status_code = _error_status_for_code(exc.code)
    logger.warning("VideoGenerationError code={} message={}", exc.code, exc.message)
    return ORJSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": exc.message,
            "detail": {"code": exc.code},
        },
    )


@app.exception_handler(KieGenerationError)
async def kie_generation_exception_handler(
    _: Request,
    exc: KieGenerationError,
) -> JSONResponse:
    """Map Kie.ai provider failures to structured HTTP errors."""
    status_code = _error_status_for_code(exc.code)
    logger.warning("KieGenerationError code={} message={}", exc.code, exc.message)
    return ORJSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": exc.message,
            "detail": {"code": exc.code},
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalize HTTPException payloads."""
    logger.warning("HTTPException status={} detail={}", exc.status_code, exc.detail)
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": "Request failed",
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return structured validation errors."""
    logger.warning("Validation error: {}", exc.errors())
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors."""
    logger.exception("Unhandled exception: {}", exc)
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


app.include_router(upload_router.router)
app.include_router(prompt_router.router)
app.include_router(video_router.router)
app.include_router(status_router.router)

app.mount("/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")
app.mount("/static", StaticFiles(directory=str(settings.static_path)), name="static")


def custom_openapi() -> dict:
    """Generate OpenAPI and patch upload multipart schema for Swagger file picker."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    apply_upload_openapi_fix(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Root welcome payload."""
    return {
        "success": True,
        "message": f"{settings.APP_NAME} is running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
