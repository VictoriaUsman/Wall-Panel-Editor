from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.db.models.job import JobStatus


class JobCreate(BaseModel):
    title: str
    wall_width_mm: float
    wall_height_mm: float


class JobUpdate(BaseModel):
    title: Optional[str] = None
    wall_width_mm: Optional[float] = None
    wall_height_mm: Optional[float] = None


class JobOut(BaseModel):
    id: str
    customer_id: str
    title: str
    wall_width_mm: float
    wall_height_mm: float
    status: JobStatus
    proof_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
