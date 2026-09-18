from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class EvidenceType(str, enum.Enum):
    CLIP = "CLIP"                     # 15s MP4 video recording (pre + event + post)
    SNAPSHOT = "SNAPSHOT"             # Full frame JPEG at trigger moment
    CROP_PERSON = "CROP_PERSON"       # Bounding box crop of person
    CROP_VEHICLE = "CROP_VEHICLE"     # Bounding box crop of vehicle
    CROP_PLATE = "CROP_PLATE"         # Localized license plate crop
    CROP_FACE = "CROP_FACE"           # High-resolution face crop

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    
    file_type = Column(Enum(EvidenceType), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    sha256_hash = Column(String(64), nullable=False, index=True) # Cryptographic proof of non-tampering
    
    metadata_json = Column(Text, default="{}") # e.g. {"fps": 15, "duration_sec": 12.5, "bbox": [...]}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    incident = relationship("Incident", back_populates="evidences")
