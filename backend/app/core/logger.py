"""Loguru logging configuration."""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import BACKEND_ROOT, get_settings


def configure_logging() -> None:
    """Configure application-wide Loguru sinks."""
    settings = get_settings()
    log_dir = BACKEND_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        level="INFO",
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )


def get_logger():
    """Return the shared Loguru logger instance."""
    return logger
