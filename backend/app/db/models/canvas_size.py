import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class CanvasSize(Base):
    __tablename__ = "canvas_sizes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    width_mm = Column(Float, nullable=False)
    height_mm = Column(Float, nullable=False)
    thickness_mm = Column(Float, nullable=False, default=18.0)
    price_cents = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    holes = relationship("Hole", back_populates="canvas_size", cascade="all, delete-orphan")
    panels = relationship("Panel", back_populates="canvas_size")
