from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class IncidentStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    # Legacy aliases
    NEW = "DETECTED"
    FALSE_POSITIVE = "CLOSED"

class IncidentSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_code = Column(String(50), unique=True, index=True, nullable=False) # e.g. INC-2026-0819
    title = Column(String(150), nullable=False)
    summary = Column(Text, nullable=False)
    incident_type = Column(String(50), nullable=False, index=True) # INTRUSION, BREACH, SUSPICIOUS_VEHICLE, etc.
    
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=True)
    
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.HIGH, nullable=False, index=True)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.DETECTED, nullable=False, index=True)
    threat_score = Column(Float, default=75.0) # 0 to 100 confidence/threat score
    
    # Context correlation
    location_name = Column(String(100), default="Border Perimeter Sector 4")
    correlated_event_ids = Column(String(255), default="") # Comma-separated rule event IDs
    tags_json = Column(Text, default="[]")
    
    # Assignment & Lifecycle
    assigned_to = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Transition timestamps & users
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    triaged_at = Column(DateTime, nullable=True)
    triaged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(50), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(50), nullable=True)
    resolution_reason = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Transition history: [{from_status, to_status, user, note, timestamp}]
    transition_history_json = Column(Text, default="[]")
    
    # Operator notes log: [{user, text, timestamp}]
    operator_notes_json = Column(Text, default="[]")

    # Relationships
    camera = relationship("Camera", back_populates="incidents")
    evidences = relationship("Evidence", back_populates="incident", cascade="all, delete-orphan")
