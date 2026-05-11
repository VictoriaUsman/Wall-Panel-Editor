import uuid
from sqlalchemy import Column, Float, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Panel(Base):
    """
    A placed panel on the wall.
    x_mm, y_mm = top-left corner in wall coordinates (mm from wall top-left).
    rotation_deg = clockwise rotation in degrees (0, 90, 180, 270 or any float).
    All coordinates are in millimetres. No pixels anywhere.
    """
    __tablename__ = "panels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    canvas_size_id = Column(UUID(as_uuid=True), ForeignKey("canvas_sizes.id"), nullable=False)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), nullable=True)
    x_mm = Column(Float, nullable=False, default=0.0)
    y_mm = Column(Float, nullable=False, default=0.0)
    rotation_deg = Column(Float, nullable=False, default=0.0)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="panels")
    canvas_size = relationship("CanvasSize", back_populates="panels")
    photo = relationship("Photo", back_populates="panels")
