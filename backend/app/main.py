"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import status as status_router
from app.api import upload as upload_router
from app.api import video as video_router
from app.core.config import get_settings
from app.core.logger import configure_logging, get_logger
from app.services.kie_client import KieClient
from app.utils.file_utils import ensure_directory

configure_logging()
logger = get_logger()
settings = get_settings()

# Ensure mount targets exist at import time (StaticFiles requires existing dirs).
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.generated_path.mkdir(parents=True, exist_ok=True)
settings.static_path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Starting {} on {}:{}", settings.APP_NAME, settings.HOST, settings.PORT)

    await ensure_directory(settings.upload_path)
    await ensure_directory(settings.generated_path)
    await ensure_directory(settings.static_path)

    kie_client = KieClient(settings=settings)
    await kie_client.startup()
    app.state.kie_client = kie_client

    logger.info("Upload directory ready: {}", settings.upload_path)
    logger.info("Generated directory ready: {}", settings.generated_path)
    yield

    await kie_client.shutdown()
    logger.info("Shutting down {}", settings.APP_NAME)


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
app.include_router(video_router.router)
app.include_router(status_router.router)

app.mount("/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")
app.mount("/static", StaticFiles(directory=str(settings.static_path)), name="static")


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Root welcome payload."""
    return {
        "success": True,
        "message": f"{settings.APP_NAME} is running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
