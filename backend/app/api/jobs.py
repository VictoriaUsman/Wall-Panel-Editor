from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.job import Job, JobStatus, VALID_TRANSITIONS
from app.core.deps import get_current_user, get_current_operator
from app.schemas.job import JobCreate, JobUpdate, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_out(j: Job) -> JobOut:
    return JobOut(
        id=str(j.id), customer_id=str(j.customer_id),
        title=j.title, wall_width_mm=j.wall_width_mm,
        wall_height_mm=j.wall_height_mm, status=j.status,
        proof_url=j.proof_url, created_at=j.created_at, updated_at=j.updated_at,
    )


async def _get_job_for_user(job_id: str, user: User, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not user.is_operator and str(job.customer_id) != str(user.id):
        raise HTTPException(403, "Access denied")
    return job


@router.post("", response_model=JobOut)
async def create_job(body: JobCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = Job(
        customer_id=user.id, title=body.title,
        wall_width_mm=body.wall_width_mm, wall_height_mm=body.wall_height_mm,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return _job_out(job)


@router.get("", response_model=List[JobOut])
async def list_jobs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.is_operator:
        result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    else:
        result = await db.execute(select(Job).where(Job.customer_id == user.id).order_by(Job.created_at.desc()))
    return [_job_out(j) for j in result.scalars().all()]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job_for_user(job_id, user, db)
    return _job_out(job)


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(job_id: str, body: JobUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job_for_user(job_id, user, db)
    if job.status not in (JobStatus.DRAFT, JobStatus.UPLOADED, JobStatus.ARRANGING):
        raise HTTPException(400, "Cannot edit job in current status")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(job, field, val)
    await db.commit()
    await db.refresh(job)
    return _job_out(job)


@router.post("/{job_id}/transition", response_model=JobOut)
async def transition_job(
    job_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Explicit status transitions. Body: {"to": "ARRANGING"}.
    Operator can perform any valid transition; customers only allowed:
      DRAFT→UPLOADED, UPLOADED→ARRANGING, PROOFING→ARRANGING (request changes),
      PROOFING→APPROVED
    """
    job = await _get_job_for_user(job_id, user, db)
    new_status_str = body.get("to")
    try:
        new_status = JobStatus(new_status_str)
    except ValueError:
        raise HTTPException(400, f"Unknown status '{new_status_str}'")

    if new_status not in VALID_TRANSITIONS.get(job.status, []):
        raise HTTPException(400, f"Invalid transition {job.status} → {new_status}")

    # Customers cannot transition to PROOFING (only operator sends proofs)
    if not user.is_operator and new_status == JobStatus.PROOFING:
        raise HTTPException(403, "Only operators can send proofs")

    job.status = new_status
    await db.commit()
    await db.refresh(job)
    return _job_out(job)


@router.post("/{job_id}/send-proof", response_model=JobOut)
async def send_proof(
    job_id: str,
    body: dict,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.ARRANGING:
        raise HTTPException(400, "Job must be in ARRANGING to send proof")

    job.proof_url = body.get("proof_url", "")
    job.status = JobStatus.PROOFING
    await db.commit()
    await db.refresh(job)
    return _job_out(job)
