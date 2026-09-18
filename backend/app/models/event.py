from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from app.core.database import Base

class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    object_class = Column(String(50), nullable=False, index=True) # person, car, truck, bus, motorcycle
    confidence = Column(Float, nullable=False)
    
    # Normalized bbox: {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.6}
    bbox_json = Column(Text, nullable=False)
    velocity_vector = Column(String(50), default="0.0,0.0")
    dwell_duration_sec = Column(Float, default=0.0)
    
    in_zone_ids = Column(String(100), default="") # comma-separated IDs
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

class RuleEvent(Base):
    __tablename__ = "rule_events"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=True)
    
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    details_json = Column(Text, default="{}")
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    is_correlated = Column(Boolean, default=False, nullable=False) # Marked True once promoted to Incident
