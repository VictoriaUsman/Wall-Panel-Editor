from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PhotoPresignRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: Optional[int] = None


class PhotoPresignResponse(BaseModel):
    photo_id: str
    upload_url: str
    method: str
    headers: dict
    storage_key: str


class PhotoConfirmRequest(BaseModel):
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    size_bytes: Optional[int] = None


class PhotoOut(BaseModel):
    id: str
    job_id: str
    filename: str
    storage_key: str
    width_px: Optional[int]
    height_px: Optional[int]
    size_bytes: Optional[int]
    upload_confirmed: bool
    url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
