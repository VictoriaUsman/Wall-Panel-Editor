from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pathlib import Path
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.job import Job, JobStatus
from app.db.models.photo import Photo
from app.core.deps import get_current_user
from app.schemas.photo import PhotoPresignRequest, PhotoPresignResponse, PhotoConfirmRequest, PhotoOut
from app.services import storage
from app.config import get_settings

router = APIRouter(tags=["photos"])
settings = get_settings()


def _photo_out(p: Photo) -> PhotoOut:
    return PhotoOut(
        id=str(p.id), job_id=str(p.job_id), filename=p.filename,
        storage_key=p.storage_key, width_px=p.width_px, height_px=p.height_px,
        size_bytes=p.size_bytes, upload_confirmed=p.upload_confirmed,
        url=storage.get_public_url(p.storage_key) if p.upload_confirmed else None,
        created_at=p.created_at,
    )


async def _get_job_for_user(job_id: str, user: User, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not user.is_operator and str(job.customer_id) != str(user.id):
        raise HTTPException(403, "Access denied")
    return job


@router.post("/jobs/{job_id}/photos/presign", response_model=PhotoPresignResponse)
async def presign_upload(
    job_id: str,
    body: PhotoPresignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _get_job_for_user(job_id, user, db)
    if job.status not in (JobStatus.DRAFT, JobStatus.UPLOADED, JobStatus.ARRANGING):
        raise HTTPException(400, "Cannot upload photos in current job status")

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    if body.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"content_type must be one of {ALLOWED_TYPES}")

    key = storage.generate_storage_key(body.filename)
    presign = storage.generate_presigned_put(key, body.content_type)

    photo = Photo(job_id=job_id, filename=body.filename, storage_key=key, size_bytes=body.size_bytes)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return PhotoPresignResponse(
        photo_id=str(photo.id),
        upload_url=presign["upload_url"],
        method=presign["method"],
        headers=presign["headers"],
        storage_key=key,
    )


@router.put("/mock-upload/{storage_key}")
async def mock_upload(storage_key: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Mock presigned PUT endpoint — accepts the raw file bytes and saves to disk.
    In production, this route does not exist; the browser PUTs directly to R2/S3.
    """
    data = await request.body()
    await storage.save_mock_upload(storage_key, data)

    result = await db.execute(select(Photo).where(Photo.storage_key == storage_key))
    photo = result.scalar_one_or_none()
    if photo:
        photo.upload_confirmed = True
        photo.size_bytes = len(data)
        await db.commit()

    return {"ok": True, "key": storage_key}


@router.post("/jobs/{job_id}/photos/{photo_id}/confirm", response_model=PhotoOut)
async def confirm_upload(
    job_id: str,
    photo_id: str,
    body: PhotoConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_job_for_user(job_id, user, db)
    result = await db.execute(select(Photo).where(Photo.id == photo_id, Photo.job_id == job_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(404, "Photo not found")

    photo.upload_confirmed = True
    if body.width_px:
        photo.width_px = body.width_px
    if body.height_px:
        photo.height_px = body.height_px
    if body.size_bytes:
        photo.size_bytes = body.size_bytes
    await db.commit()
    await db.refresh(photo)
    return _photo_out(photo)


@router.get("/jobs/{job_id}/photos", response_model=List[PhotoOut])
async def list_photos(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_job_for_user(job_id, user, db)
    result = await db.execute(select(Photo).where(Photo.job_id == job_id).order_by(Photo.created_at))
    return [_photo_out(p) for p in result.scalars().all()]


@router.delete("/jobs/{job_id}/photos/{photo_id}", status_code=204)
async def delete_photo(
    job_id: str,
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_job_for_user(job_id, user, db)
    result = await db.execute(select(Photo).where(Photo.id == photo_id, Photo.job_id == job_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(404, "Photo not found")
    await db.delete(photo)
    await db.commit()


@router.get("/uploads/{storage_key}")
async def serve_upload(storage_key: str):
    """Serve locally stored mock uploads."""
    path = storage.local_path(storage_key)
    if not path.exists():
        raise HTTPException(404, "File not found")
    ext = path.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(str(path), media_type=media_types.get(ext, "application/octet-stream"))
