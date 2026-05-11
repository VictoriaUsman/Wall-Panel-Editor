import uuid
from sqlalchemy import Column, String, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Hole(Base):
    """
    Hole position in mm relative to panel top-left corner.
    Never stored as pixels or normalized percentages.
    """
    __tablename__ = "holes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canvas_size_id = Column(UUID(as_uuid=True), ForeignKey("canvas_sizes.id"), nullable=False)
    label = Column(String, nullable=False, default="D-ring")
    x_mm = Column(Float, nullable=False)  # from panel left edge
    y_mm = Column(Float, nullable=False)  # from panel top edge
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    canvas_size = relationship("CanvasSize", back_populates="holes")
