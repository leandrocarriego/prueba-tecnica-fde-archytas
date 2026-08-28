"""Application settings, loaded from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# There is one .env, at the repository root. Resolving it from this file rather
# than from the working directory means `uv run uvicorn` from `backend/`, pytest
# from the root and a Celery worker from anywhere all read the same file.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the Cordillera platform."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    PROJECT_NAME: str = "Plataforma Cordillera"
    ENVIRONMENT: str = "DEVELOPMENT"
    API_VERSION: str = "v1"

    # --- Security ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    # --- Database ---
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # --- Message broker (Celery) ---
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # --- SIGProv portal (read-only source system) ---
    # Credentials belong to a third party and live only here: never in the database,
    # never in the repository, never in a log.
    PORTAL_BASE_URL: str = "https://prueba-tecnica-portal.vercel.app"
    PORTAL_USER: str = ""
    PORTAL_PASSWORD: str = ""
    PORTAL_HEADLESS: bool = True
    # Download links issued by the portal expire quickly; a job must consume them
    # within this window or re-request the link.
    PORTAL_DOWNLOAD_TTL_SECONDS: int = 45
    PORTAL_NAVIGATION_TIMEOUT_MS: int = 15_000

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def broker_url(self) -> str:
        """AMQP URL for Celery, derived from the RabbitMQ settings unless overridden."""
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"
        )

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.upper() == "DEVELOPMENT"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


settings = get_settings()
