from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.job import Job, JobStatus
from app.db.models.panel import Panel
from app.core.deps import get_current_user
from app.schemas.panel import PanelCreate, PanelUpdate, PanelBatchUpdate, PanelOut
import uuid as _uuid

router = APIRouter(tags=["panels"])


def _panel_out(p: Panel) -> PanelOut:
    return PanelOut(
        id=str(p.id), job_id=str(p.job_id), canvas_size_id=str(p.canvas_size_id),
        photo_id=str(p.photo_id) if p.photo_id else None,
        x_mm=p.x_mm, y_mm=p.y_mm, rotation_deg=p.rotation_deg,
        sort_order=p.sort_order, created_at=p.created_at, updated_at=p.updated_at,
    )


async def _get_editable_job(job_id: str, user: User, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not user.is_operator and str(job.customer_id) != str(user.id):
        raise HTTPException(403, "Access denied")
    # Customer editor is read-only during PROOFING (unless operator)
    if not user.is_operator and job.status == JobStatus.PROOFING:
        raise HTTPException(403, "Layout is read-only while proof is under review")
    if job.status in (JobStatus.APPROVED, JobStatus.PRINTED, JobStatus.SHIPPED):
        raise HTTPException(400, "Job is finalised; layout cannot be changed")
    return job


@router.get("/jobs/{job_id}/panels", response_model=List[PanelOut])
async def list_panels(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not user.is_operator and str(job.customer_id) != str(user.id):
        raise HTTPException(403, "Access denied")
    result = await db.execute(select(Panel).where(Panel.job_id == job_id).order_by(Panel.sort_order))
    return [_panel_out(p) for p in result.scalars().all()]


@router.post("/jobs/{job_id}/panels", response_model=PanelOut)
async def create_panel(
    job_id: str, body: PanelCreate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_editable_job(job_id, user, db)
    panel = Panel(
        job_id=job_id, canvas_size_id=body.canvas_size_id,
        photo_id=body.photo_id, x_mm=body.x_mm, y_mm=body.y_mm,
        rotation_deg=body.rotation_deg,
    )
    db.add(panel)
    await db.commit()
    await db.refresh(panel)
    return _panel_out(panel)


@router.patch("/jobs/{job_id}/panels/{panel_id}", response_model=PanelOut)
async def update_panel(
    job_id: str, panel_id: str, body: PanelUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_editable_job(job_id, user, db)
    result = await db.execute(select(Panel).where(Panel.id == panel_id, Panel.job_id == job_id))
    panel = result.scalar_one_or_none()
    if not panel:
        raise HTTPException(404, "Panel not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(panel, field, val)
    await db.commit()
    await db.refresh(panel)
    return _panel_out(panel)


@router.delete("/jobs/{job_id}/panels/{panel_id}", status_code=204)
async def delete_panel(
    job_id: str, panel_id: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_editable_job(job_id, user, db)
    result = await db.execute(select(Panel).where(Panel.id == panel_id, Panel.job_id == job_id))
    panel = result.scalar_one_or_none()
    if not panel:
        raise HTTPException(404, "Panel not found")
    await db.delete(panel)
    await db.commit()


@router.put("/jobs/{job_id}/panels", response_model=List[PanelOut])
async def batch_upsert_panels(
    job_id: str, body: PanelBatchUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """
    Auto-save endpoint: replaces all panels for a job with the submitted list.
    Called on every editor change (debounced 500ms on the frontend).
    """
    await _get_editable_job(job_id, user, db)

    # Delete panels not in the new list
    incoming_ids = {p.id for p in body.panels if p.id}
    existing_result = await db.execute(select(Panel).where(Panel.job_id == job_id))
    existing = existing_result.scalars().all()
    for p in existing:
        if str(p.id) not in incoming_ids:
            await db.delete(p)

    # Validate photo_ids exist — null out any that were deleted to avoid FK violations
    valid_photo_ids: set[str] = set()
    if any(pu.photo_id for pu in body.panels):
        from app.db.models.photo import Photo
        photo_ids_to_check = [pu.photo_id for pu in body.panels if pu.photo_id]
        photos_result = await db.execute(
            select(Photo.id).where(Photo.id.in_(photo_ids_to_check))
        )
        valid_photo_ids = {str(r) for r in photos_result.scalars().all()}

    out = []
    for i, pu in enumerate(body.panels):
        if pu.id:
            result = await db.execute(select(Panel).where(Panel.id == pu.id, Panel.job_id == job_id))
            panel = result.scalar_one_or_none()
            if not panel:
                panel = Panel(id=_uuid.UUID(pu.id), job_id=job_id)
                db.add(panel)
        else:
            panel = Panel(job_id=job_id)
            db.add(panel)

        panel.canvas_size_id = pu.canvas_size_id
        panel.photo_id = pu.photo_id if (pu.photo_id and pu.photo_id in valid_photo_ids) else None
        panel.x_mm = pu.x_mm
        panel.y_mm = pu.y_mm
        panel.rotation_deg = pu.rotation_deg
        panel.sort_order = i
        out.append(panel)

    await db.commit()
    for p in out:
        await db.refresh(p)
    return [_panel_out(p) for p in out]
