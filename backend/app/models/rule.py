from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from app.core.database import Base

class RuleSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class RuleEventType(str, enum.Enum):
    PERIMETER_BREACH = "PERIMETER_BREACH"
    ZONE_INTRUSION = "ZONE_INTRUSION"
    LOITERING = "LOITERING"
    VIRTUAL_FENCE_CROSSING = "VIRTUAL_FENCE_CROSSING"
    STATIONARY_OBJECT = "STATIONARY_OBJECT"
    STATIONARY_VEHICLE = "STATIONARY_VEHICLE"
    UNUSUAL_VEHICLE_STOP = "UNUSUAL_VEHICLE_STOP"
    WRONG_WAY = "WRONG_WAY"
    RESTRICTED_ZONE_ACTIVITY = "RESTRICTED_ZONE_ACTIVITY"
    NIGHT_MOVEMENT = "NIGHT_MOVEMENT"
    CROWD_DENSITY = "CROWD_DENSITY"
    CROWD_FORMATION = "CROWD_FORMATION"
    ABANDONED_OBJECT = "ABANDONED_OBJECT"
    REMOVED_OBJECT = "REMOVED_OBJECT"
    REPEATED_MOVEMENT = "REPEATED_MOVEMENT"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    SUSPICIOUS_ROUTE = "SUSPICIOUS_ROUTE"
    FIRE_DETECTED = "FIRE_DETECTED"
    SMOKE_DETECTED = "SMOKE_DETECTED"
    FALL_DETECTED = "FALL_DETECTED"
    DANGEROUS_OBJECT_DETECTED = "DANGEROUS_OBJECT_DETECTED"
    ACTION_DETECTED = "ACTION_DETECTED"
    POSE_DETECTED = "POSE_DETECTED"
    WATCHLIST_FACE_MATCH = "WATCHLIST_FACE_MATCH"
    WATCHLIST_PLATE_MATCH = "WATCHLIST_PLATE_MATCH"

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    event_type = Column(Enum(RuleEventType), nullable=False)
    severity = Column(Enum(RuleSeverity), default=RuleSeverity.HIGH, nullable=False)
    
    # Applicable cameras: e.g. [1, 2] or [] for all
    camera_ids_json = Column(Text, default="[]", nullable=False)
    
    # Conditions: target_classes (["person", "car"]), min_confidence, dwell_sec, etc.
    conditions_json = Column(Text, default="{}", nullable=False)
    
    # Schedule: e.g. {"always": false, "start_time": "20:00", "end_time": "06:00", "days": [0,1,2,3,4,5,6]}
    schedule_json = Column(Text, default='{"always": true}', nullable=False)
    
    cooldown_seconds = Column(Integer, default=30)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
