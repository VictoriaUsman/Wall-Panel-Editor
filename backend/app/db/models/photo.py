import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)  # path in object storage / local disk
    width_px = Column(Integer, nullable=True)
    height_px = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    upload_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="photos")
    panels = relationship("Panel", back_populates="photo")
