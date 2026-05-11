from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.canvas_size import CanvasSize
from app.db.models.hole import Hole
from app.core.deps import get_current_user, get_current_operator
from app.schemas.catalog import CanvasSizeCreate, CanvasSizeUpdate, CanvasSizeOut, HoleIn, HoleOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _size_out(s: CanvasSize) -> CanvasSizeOut:
    return CanvasSizeOut(
        id=str(s.id), name=s.name, width_mm=s.width_mm, height_mm=s.height_mm,
        thickness_mm=s.thickness_mm, price_cents=s.price_cents, active=s.active,
        holes=[HoleOut(id=str(h.id), canvas_size_id=str(h.canvas_size_id),
                       label=h.label, x_mm=h.x_mm, y_mm=h.y_mm) for h in (s.holes or [])],
        created_at=s.created_at,
    )


@router.get("", response_model=List[CanvasSizeOut])
async def list_sizes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(CanvasSize)
    if not user.is_operator:
        query = query.where(CanvasSize.active == True)
    result = await db.execute(query.order_by(CanvasSize.name))
    sizes = result.scalars().all()
    # Eager load holes
    for s in sizes:
        await db.refresh(s, ["holes"])
    return [_size_out(s) for s in sizes]


@router.post("", response_model=CanvasSizeOut)
async def create_size(
    body: CanvasSizeCreate,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    size = CanvasSize(**body.model_dump())
    db.add(size)
    await db.commit()
    await db.refresh(size, ["holes"])
    return _size_out(size)


@router.patch("/{size_id}", response_model=CanvasSizeOut)
async def update_size(
    size_id: str,
    body: CanvasSizeUpdate,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CanvasSize).where(CanvasSize.id == size_id))
    size = result.scalar_one_or_none()
    if not size:
        raise HTTPException(404, "Size not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(size, field, val)
    await db.commit()
    await db.refresh(size, ["holes"])
    return _size_out(size)


@router.post("/{size_id}/holes", response_model=HoleOut)
async def add_hole(
    size_id: str,
    body: HoleIn,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CanvasSize).where(CanvasSize.id == size_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Size not found")
    hole = Hole(canvas_size_id=size_id, label=body.label, x_mm=body.x_mm, y_mm=body.y_mm)
    db.add(hole)
    await db.commit()
    await db.refresh(hole)
    return HoleOut(id=str(hole.id), canvas_size_id=str(hole.canvas_size_id),
                   label=hole.label, x_mm=hole.x_mm, y_mm=hole.y_mm)


@router.patch("/{size_id}/holes/{hole_id}", response_model=HoleOut)
async def update_hole(
    size_id: str, hole_id: str, body: HoleIn,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Hole).where(Hole.id == hole_id, Hole.canvas_size_id == size_id))
    hole = result.scalar_one_or_none()
    if not hole:
        raise HTTPException(404, "Hole not found")
    hole.label = body.label
    hole.x_mm = body.x_mm
    hole.y_mm = body.y_mm
    await db.commit()
    await db.refresh(hole)
    return HoleOut(id=str(hole.id), canvas_size_id=str(hole.canvas_size_id),
                   label=hole.label, x_mm=hole.x_mm, y_mm=hole.y_mm)


@router.delete("/{size_id}/holes/{hole_id}", status_code=204)
async def delete_hole(
    size_id: str, hole_id: str,
    operator: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Hole).where(Hole.id == hole_id, Hole.canvas_size_id == size_id))
    hole = result.scalar_one_or_none()
    if not hole:
        raise HTTPException(404, "Hole not found")
    await db.delete(hole)
    await db.commit()
