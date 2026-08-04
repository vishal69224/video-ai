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

    # Credit-safe mode: Gemma prompt only — never call Kie.ai / never spend credits.
    DEVELOPMENT_MODE: bool = False

    UPLOAD_FOLDER: str = "app/uploads"
    GENERATED_FOLDER: str = "app/generated"
    STATIC_FOLDER: str = "app/static"

    MAX_UPLOAD_SIZE: int = 20_971_520  # 20 MB
    MAX_UPLOAD_COUNT: int = 10
    MIN_UPLOAD_COUNT: int = 1

    # Stored as comma-separated strings in .env for simple dotenv parsing.
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,webp"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Public base URL used to build absolute image URLs for Kie.ai.
    # Localhost is not reachable by Kie — use an ngrok/tunnel URL in production tests.
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    KIE_API_KEY: str = ""
    KIE_BASE_URL: str = "https://api.kie.ai"
    # Official File Upload API host (docs.kie.ai/file-upload-api/quickstart)
    KIE_FILE_BASE_URL: str = "https://kieai.redpandaai.co"
    KIE_TIMEOUT: float = 60.0
    KIE_MODEL: str = "wan/2-7-image-to-video"
    KIE_RESOLUTION: str = "1080p"
    KIE_DURATION: str = "5"

    # Vision AI provider selection: "openrouter" | "ollama"
    AI_PROVIDER: str = "openrouter"

    OLLAMA_MODEL: str = "gemma3:4b"
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_TIMEOUT: float = 120.0

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemma-4-26b-a4b-it:free"
    OPENROUTER_TIMEOUT: float = 120.0

    # MongoDB — metadata only (no MP4 binaries).
    MONGODB_URI: str = "mongodb://127.0.0.1:27017"
    MONGODB_DB: str = "video_ai"

    @property
    def ai_timeout(self) -> float:
        """Timeout for the active vision provider."""
        provider = (self.AI_PROVIDER or "openrouter").strip().lower()
        if provider == "ollama":
            return float(self.OLLAMA_TIMEOUT)
        return float(self.OPENROUTER_TIMEOUT)

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

    @property
    def display_duration(self) -> str:
        """Human-readable duration label for library cards."""
        try:
            seconds = max(1, int(str(self.KIE_DURATION).strip()))
        except ValueError:
            seconds = 5
        minutes, rem = divmod(seconds, 60)
        return f"{minutes}:{rem:02d}"

    @property
    def display_resolution(self) -> str:
        """Human-readable resolution label for library cards."""
        resolution = self.KIE_RESOLUTION.strip().lower()
        if resolution in {"1080p", "1080"}:
            return "1080 × 1920"
        if resolution in {"720p", "720"}:
            return "720 × 1280"
        return self.KIE_RESOLUTION or "1080 × 1920"


@lru_cache
def get_settings() -> Settings:
    """Cached settings dependency for FastAPI."""
    return Settings()


def reload_settings() -> Settings:
    """Clear cached settings and reload from environment / .env."""
    get_settings.cache_clear()
    return get_settings()
