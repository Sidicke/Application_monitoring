"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/energy_monitor"

    @property
    def async_database_url(self) -> str:
        """Convert postgres:// standard urls provided by Render to asyncpg valid ones."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # asyncpg uses 'ssl' keyword instead of 'sslmode'
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=", 1)
            
        return url

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production-with-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 h

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "MONITORING"
    DEBUG: bool = True

    # ── Default billing ───────────────────────────────────────
    DEFAULT_KWH_PRICE: float = 0.12  # USD / kWh
    DEFAULT_CURRENCY: str = "XOF"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
