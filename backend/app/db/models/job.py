import uuid
import enum
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class JobStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    ARRANGING = "ARRANGING"
    PROOFING = "PROOFING"
    APPROVED = "APPROVED"
    PRINTED = "PRINTED"
    SHIPPED = "SHIPPED"


# Valid forward transitions only
VALID_TRANSITIONS: dict[JobStatus, list[JobStatus]] = {
    JobStatus.DRAFT: [JobStatus.UPLOADED],
    JobStatus.UPLOADED: [JobStatus.ARRANGING],
    JobStatus.ARRANGING: [JobStatus.PROOFING],
    JobStatus.PROOFING: [JobStatus.APPROVED, JobStatus.ARRANGING],  # ARRANGING = request changes
    JobStatus.APPROVED: [JobStatus.PRINTED],
    JobStatus.PRINTED: [JobStatus.SHIPPED],
    JobStatus.SHIPPED: [],
}


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    wall_width_mm = Column(Float, nullable=False)
    wall_height_mm = Column(Float, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.DRAFT, nullable=False)
    proof_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("User", back_populates="jobs", foreign_keys=[customer_id])
    photos = relationship("Photo", back_populates="job", cascade="all, delete-orphan")
    panels = relationship("Panel", back_populates="job", cascade="all, delete-orphan")
