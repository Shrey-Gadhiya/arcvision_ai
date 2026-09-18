from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class SegmentType(str, enum.Enum):
    CONTINUOUS = "CONTINUOUS"
    MOTION = "MOTION"
    EVENT = "EVENT"

class RecordingSegment(Base):
    __tablename__ = "recording_segments"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    duration_sec = Column(Float, nullable=False)
    
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    segment_type = Column(Enum(SegmentType), default=SegmentType.CONTINUOUS, nullable=False)
    
    motion_score = Column(Float, default=0.0)
    has_objects = Column(Boolean, default=False)
    objects_detected_json = Column(Text, default="[]", nullable=False) # e.g. ["person", "car"]
    sha256_hash = Column(String(64), nullable=True)
    is_protected = Column(Boolean, default=False, nullable=False, index=True) # Protected evidence recordings cannot be auto-pruned
    codec = Column(String(50), default="H.264 / MP4", nullable=False)
    resolution = Column(String(50), default="1280x720", nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    camera = relationship("Camera", back_populates="recording_segments")
