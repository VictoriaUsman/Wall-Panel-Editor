from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class HoleIn(BaseModel):
    label: str = "D-ring"
    x_mm: float
    y_mm: float


class HoleOut(BaseModel):
    id: str
    canvas_size_id: str
    label: str
    x_mm: float
    y_mm: float

    class Config:
        from_attributes = True


class CanvasSizeCreate(BaseModel):
    name: str
    width_mm: float
    height_mm: float
    thickness_mm: float = 18.0
    price_cents: int = 0


class CanvasSizeUpdate(BaseModel):
    name: Optional[str] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    thickness_mm: Optional[float] = None
    price_cents: Optional[int] = None
    active: Optional[bool] = None


class CanvasSizeOut(BaseModel):
    id: str
    name: str
    width_mm: float
    height_mm: float
    thickness_mm: float
    price_cents: int
    active: bool
    holes: List[HoleOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
