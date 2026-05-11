from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://wpd:wpd@db:5432/wpd"
    SECRET_KEY: str = "change-me-in-production-use-32-random-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Mock storage: files saved to local disk, presigned URL is a local endpoint
    STORAGE_MOCK: bool = True
    UPLOAD_DIR: str = "/app/uploads"
    MOCK_UPLOAD_BASE_URL: str = "http://localhost:8000"

    OPERATOR_EMAIL: str = "operator@woodpanel.com"

    # Railway injects PORT; used in CMD
    PORT: int = 8000

    @model_validator(mode="after")
    def fix_db_url(self) -> "Settings":
        # Railway provides postgresql://, SQLAlchemy async needs postgresql+asyncpg://
        url = self.DATABASE_URL
        if url and url.startswith("postgresql://") and "+asyncpg" not in url:
            self.DATABASE_URL = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
