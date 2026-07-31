"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the Video AI backend."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Video AI Backend"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    UPLOAD_FOLDER: str = "app/uploads"
    GENERATED_FOLDER: str = "app/generated"
    STATIC_FOLDER: str = "app/static"

    MAX_UPLOAD_SIZE: int = 20_971_520  # 20 MB
    MAX_UPLOAD_COUNT: int = 10
    MIN_UPLOAD_COUNT: int = 1

    # Stored as comma-separated strings in .env for simple dotenv parsing.
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,webp"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    KIE_API_KEY: str = ""
    KIE_BASE_URL: str = ""

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def normalize_extensions(cls, value: object) -> str:
        if isinstance(value, (list, set, tuple)):
            return ",".join(str(item).strip().lower().lstrip(".") for item in value)
        return str(value)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def normalize_cors(cls, value: object) -> str:
        if isinstance(value, (list, tuple)):
            return ",".join(str(item).strip() for item in value)
        return str(value)

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            item.strip().lower().lstrip(".")
            for item in self.ALLOWED_EXTENSIONS.split(",")
            if item.strip()
        }

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_FOLDER)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def generated_path(self) -> Path:
        path = Path(self.GENERATED_FOLDER)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def static_path(self) -> Path:
        path = Path(self.STATIC_FOLDER)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    """Cached settings dependency for FastAPI."""
    return Settings()
