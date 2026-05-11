"""
PDF and print-master export endpoints.
"""
import io
import zipfile
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from PIL import Image

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.job import Job, JobStatus
from app.db.models.panel import Panel
from app.db.models.canvas_size import CanvasSize
from app.db.models.hole import Hole
from app.db.models.photo import Photo
from app.core.deps import get_current_user, get_current_operator
from app.services.pdf import (
    build_tiled_template, build_reference_sheet,
    WallLayout, PanelData, HoleData,
)
from app.services.geometry import fallback_hole
from app.services import storage

router = APIRouter(tags=["pdfs"])


async def _build_layout(job: Job, db: AsyncSession) -> WallLayout:
    result = await db.execute(select(Panel).where(Panel.job_id == job.id).order_by(Panel.sort_order))
    panels = result.scalars().all()

    panel_data_list: List[PanelData] = []
    for i, p in enumerate(panels):
        cs_result = await db.execute(select(CanvasSize).where(CanvasSize.id == p.canvas_size_id))
        cs = cs_result.scalar_one_or_none()
        if not cs:
            continue

        holes_result = await db.execute(select(Hole).where(Hole.canvas_size_id == cs.id))
        raw_holes = holes_result.scalars().all()

        has_hole_config = bool(raw_holes)
        if raw_holes:
            holes = [HoleData(label=h.label, x_mm=h.x_mm, y_mm=h.y_mm) for h in raw_holes]
        else:
            fb = fallback_hole(cs.width_mm, cs.height_mm)
            holes = [HoleData(label="centre (fallback)", x_mm=fb.x_mm, y_mm=fb.y_mm)]

        panel_data_list.append(PanelData(
            panel_id=str(p.id),
            label=f"P{i+1}",
            x_mm=p.x_mm, y_mm=p.y_mm,
            width_mm=cs.width_mm, height_mm=cs.height_mm,
            rotation_deg=p.rotation_deg,
            holes=holes,
            has_hole_config=has_hole_config,
        ))

    return WallLayout(
        wall_width_mm=job.wall_width_mm,
        wall_height_mm=job.wall_height_mm,
        panels=panel_data_list,
        job_title=job.title,
    )


@router.get("/jobs/{job_id}/pdf/template")
async def download_template(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download 1:1 tiled hanging template PDF."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not user.is_operator and str(job.customer_id) != str(user.id):
        raise HTTPException(403)
    if job.status not in (JobStatus.PROOFING, JobStatus.APPROVED, JobStatus.PRINTED, JobStatus.SHIPPED):
        raise HTTPException(400, "Template only available after proof is sent")

    layout = await _build_layout(job, db)
    pdf_bytes = build_tiled_template(layout)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="template_{job.title}.pdf"'},
    )


@router.get("/jobs/{job_id}/pdf/reference")
async def download_reference(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download scaled reference sheet PDF."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not user.is_operator and str(job.customer_id) != str(user.id):
        raise HTTPException(403)
    if job.status not in (JobStatus.PROOFING, JobStatus.APPROVED, JobStatus.PRINTED, JobStatus.SHIPPED):
        raise HTTPException(400, "Reference sheet only available after proof is sent")

    layout = await _build_layout(job, db)
    pdf_bytes = build_reference_sheet(layout)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reference_{job.title}.pdf"'},
    )


@router.get("/jobs/{job_id}/export/print-masters")
async def download_print_masters(
    job_id: str,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """
    Operator: download zip of per-panel 300 dpi print-master PNGs + MANIFEST.txt.
    Only available for APPROVED+ jobs.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in (JobStatus.APPROVED, JobStatus.PRINTED, JobStatus.SHIPPED):
        raise HTTPException(400, "Print masters only available for approved jobs")

    panels_result = await db.execute(select(Panel).where(Panel.job_id == job.id).order_by(Panel.sort_order))
    panels = panels_result.scalars().all()

    buf = io.BytesIO()
    manifest_lines = ["MANIFEST.txt — Wood Panel Print Masters", f"Job: {job.title}", ""]

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, panel in enumerate(panels):
            cs_result = await db.execute(select(CanvasSize).where(CanvasSize.id == panel.canvas_size_id))
            cs = cs_result.scalar_one_or_none()
            if not cs:
                continue

            photo_filename = "no_photo"
            img = None
            if panel.photo_id:
                photo_result = await db.execute(select(Photo).where(Photo.id == panel.photo_id))
                photo = photo_result.scalar_one_or_none()
                if photo:
                    photo_filename = photo.filename
                    local = storage.local_path(photo.storage_key)
                    if local.exists():
                        try:
                            img = Image.open(str(local))
                        except Exception:
                            img = None

            # 300 dpi: pixels = mm/25.4 * 300
            target_w = int(cs.width_mm / 25.4 * 300)
            target_h = int(cs.height_mm / 25.4 * 300)

            if img:
                img = img.convert("RGB").resize((target_w, target_h), Image.LANCZOS)
            else:
                img = Image.new("RGB", (target_w, target_h), (240, 240, 240))

            panel_buf = io.BytesIO()
            img.save(panel_buf, format="PNG")
            zname = f"panel_{i+1:02d}_{cs.name.replace(' ', '_')}.png"
            zf.writestr(zname, panel_buf.getvalue())

            manifest_lines.append(
                f"panel_{i+1:02d}: size={cs.name} ({cs.width_mm}x{cs.height_mm}mm) "
                f"photo={photo_filename} file={zname}"
            )

        zf.writestr("MANIFEST.txt", "\n".join(manifest_lines))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="print_masters_{job.title}.zip"'},
    )
