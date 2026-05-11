from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://wpd:wpd@db:5432/wpd"
    SECRET_KEY: str = "change-me-in-production-use-32-random-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    STORAGE_MOCK: bool = True
    UPLOAD_DIR: str = "/app/uploads"
    MOCK_UPLOAD_BASE_URL: str = "http://localhost:8000"

    OPERATOR_EMAIL: str = "operator@woodpanel.com"

    PORT: int = 8000

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg(cls, v: str) -> str:
        # Railway (and most Postgres providers) emit postgresql://.
        # SQLAlchemy async requires postgresql+asyncpg://.
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
