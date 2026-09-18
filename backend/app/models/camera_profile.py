from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from app.core.database import Base

class CameraAIProfile(Base):
    __tablename__ = "camera_ai_profiles"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Task Enablement Flags
    person_detection = Column(Boolean, default=True, nullable=False)
    vehicle_detection = Column(Boolean, default=True, nullable=False)
    anpr = Column(Boolean, default=True, nullable=False)
    face_recognition = Column(Boolean, default=True, nullable=False)
    pose_estimation = Column(Boolean, default=False, nullable=False)
    fall_detection = Column(Boolean, default=True, nullable=False)
    fire_smoke = Column(Boolean, default=True, nullable=False)
    weapon_detection = Column(Boolean, default=False, nullable=False)
    action_recognition = Column(Boolean, default=False, nullable=False)
    crowd_analysis = Column(Boolean, default=True, nullable=False)
    behavior_analytics = Column(Boolean, default=True, nullable=False)
    attribute_analysis = Column(Boolean, default=False, nullable=False)

    # Frame Sampling Intervals (Run specialized model every N frames)
    person_interval_frames = Column(Integer, default=2, nullable=False)
    vehicle_interval_frames = Column(Integer, default=2, nullable=False)
    pose_interval_frames = Column(Integer, default=3, nullable=False)
    fall_interval_frames = Column(Integer, default=2, nullable=False)
    fire_smoke_interval_frames = Column(Integer, default=5, nullable=False)
    weapon_interval_frames = Column(Integer, default=5, nullable=False)
    action_interval_frames = Column(Integer, default=4, nullable=False)
    crowd_interval_frames = Column(Integer, default=5, nullable=False)
    attribute_interval_frames = Column(Integer, default=6, nullable=False)

    # Model Confidence Thresholds
    detection_threshold = Column(Float, default=0.35, nullable=False)
    face_threshold = Column(Float, default=0.50, nullable=False)
    anpr_threshold = Column(Float, default=0.45, nullable=False)
    pose_threshold = Column(Float, default=0.40, nullable=False)
    fall_threshold = Column(Float, default=0.65, nullable=False)
    fire_smoke_threshold = Column(Float, default=0.40, nullable=False)
    weapon_threshold = Column(Float, default=0.50, nullable=False)
    action_threshold = Column(Float, default=0.60, nullable=False)
    crowd_density_threshold = Column(Integer, default=8, nullable=False)

    # Persistence Duration Thresholds (seconds)
    fire_smoke_persistence_sec = Column(Float, default=1.5, nullable=False)
    fall_persistence_sec = Column(Float, default=2.0, nullable=False)
    weapon_persistence_sec = Column(Float, default=0.5, nullable=False)
    crowd_persistence_sec = Column(Float, default=5.0, nullable=False)

    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
