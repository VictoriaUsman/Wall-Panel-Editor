from pydantic_settings import BaseSettings
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

    # Operator email suffix (simple: any user with is_operator=True)
    OPERATOR_EMAIL: str = "operator@woodpanel.com"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
