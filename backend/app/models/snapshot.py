from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class TrackedSnapshot(Base):
    __tablename__ = "tracked_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    object_class = Column(String(50), nullable=False, index=True) # e.g. "person", "car", "truck"
    confidence = Column(Float, nullable=False)
    
    clean_image_path = Column(String(500), nullable=False)     # Pristine raw frame without overlays
    annotated_image_path = Column(String(500), nullable=False) # Bounding box + tactical metadata overlay
    crop_image_path = Column(String(500), nullable=False)      # Tightly cropped object for fast visual triage
    
    box_json = Column(Text, nullable=False)                     # JSON string: [x1, y1, x2, y2]
    quality_score = Column(Float, default=1.0)                 # Resolution & sharpness score
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    camera = relationship("Camera", back_populates="snapshots")
