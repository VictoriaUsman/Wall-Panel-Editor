from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PanelCreate(BaseModel):
    canvas_size_id: str
    photo_id: Optional[str] = None
    x_mm: float = 0.0
    y_mm: float = 0.0
    rotation_deg: float = 0.0


class PanelUpdate(BaseModel):
    canvas_size_id: Optional[str] = None
    photo_id: Optional[str] = None
    x_mm: Optional[float] = None
    y_mm: Optional[float] = None
    rotation_deg: Optional[float] = None


class PanelBatchUpdate(BaseModel):
    """Used for auto-save: send the full list of panels for a job."""
    panels: List["PanelUpsert"]


class PanelUpsert(BaseModel):
    id: Optional[str] = None  # None = create new
    canvas_size_id: str
    photo_id: Optional[str] = None
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    sort_order: int = 0


class PanelOut(BaseModel):
    id: str
    job_id: str
    canvas_size_id: str
    photo_id: Optional[str]
    x_mm: float
    y_mm: float
    rotation_deg: float
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
