"""
Mock storage service.

In production, swap generate_presigned_put() for a real S3/R2 presigned URL.
The confirm_upload() step would verify the object exists in the bucket.
Local files are served via /uploads/{key} on the FastAPI app.
"""
import os
import uuid
from pathlib import Path
from app.config import get_settings

settings = get_settings()


def _upload_dir() -> Path:
    p = Path(settings.UPLOAD_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_storage_key(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"{uuid.uuid4()}{ext}"


def generate_presigned_put(storage_key: str, content_type: str) -> dict:
    """
    Returns a mock presigned PUT response.
    In production: boto3 / r2 generate_presigned_url('put_object', ...).
    """
    return {
        "upload_url": f"/api/mock-upload/{storage_key}",
        "storage_key": storage_key,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
    }


def get_public_url(storage_key: str) -> str:
    return f"/api/uploads/{storage_key}"


def local_path(storage_key: str) -> Path:
    return _upload_dir() / storage_key


async def save_mock_upload(storage_key: str, data: bytes) -> None:
    import aiofiles
    path = local_path(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)
