from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class CameraStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"

class StreamType(str, enum.Enum):
    RTSP = "RTSP"
    FILE = "FILE"
    SYNTHETIC = "SYNTHETIC"
    WEBCAM = "WEBCAM"

class CameraRecordingMode(str, enum.Enum):
    CONTINUOUS = "CONTINUOUS"
    MOTION_ONLY = "MOTION_ONLY"
    EVENT_ONLY = "EVENT_ONLY"
    DISABLED = "DISABLED"

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    rtsp_url = Column(String(500), nullable=False)
    stream_type = Column(Enum(StreamType), default=StreamType.SYNTHETIC, nullable=False)
    group_name = Column(String(50), default="Perimeter North", nullable=False)
    
    # Multi-role stream inputs (Frigate-class stream decoupling)
    detect_stream_url = Column(String(500), nullable=True)  # Low-res stream for fast AI detection
    record_stream_url = Column(String(500), nullable=True)  # High-res stream for lossless archival
    audio_stream_url = Column(String(500), nullable=True)   # Dedicated audio channel
    
    # Recording & Retention configuration
    recording_mode = Column(Enum(CameraRecordingMode), default=CameraRecordingMode.CONTINUOUS, nullable=False)
    retention_days = Column(Integer, default=7, nullable=False)
    retention_events_days = Column(Integer, default=30, nullable=False)
    pre_event_seconds = Column(Integer, default=5, nullable=False)
    post_event_seconds = Column(Integer, default=15, nullable=False)
    
    # Operational profile & feature toggles (Full global & per-camera customization)
    active_profile = Column(String(50), default="NORMAL", nullable=False) # NORMAL, NIGHT, HIGH_SECURITY, etc.
    motion_detection_enabled = Column(Boolean, default=True, nullable=False)
    anpr_enabled = Column(Boolean, default=True, nullable=False) # Enable all vehicle license plate detection
    drone_detection_enabled = Column(Boolean, default=True, nullable=False) # SkyShield UAV & aerial threat detector
    face_concealment_enabled = Column(Boolean, default=True, nullable=False) # Masking / Balaclava / Hidden face detector
    one_way_lane_enabled = Column(Boolean, default=True, nullable=False) # Wrong-way driving & traffic lane flow
    weapon_detection_enabled = Column(Boolean, default=True, nullable=False) # Firearms, knives & suspicious objects
    people_counting_enabled = Column(Boolean, default=True, nullable=False) # Bidirectional line crossing In/Out counters
    face_recognition_enabled = Column(Boolean, default=True, nullable=False) # YuNet + SFace Biometric Watchlist Matching
    cross_camera_reid_enabled = Column(Boolean, default=True, nullable=False) # Multi-camera Re-ID & Journey Tracking
    motion_threshold = Column(Integer, default=25, nullable=False) # 1-100 sensitivity
    motion_min_area = Column(Integer, default=500, nullable=False) # min contour pixel area
    
    # Tactical location & geospatial metadata
    location = Column(String(100), default="Sector 4 - Alpha Outpost")
    latitude = Column(Float, default=26.8500)
    longitude = Column(Float, default=85.2000)
    altitude_m = Column(Float, default=120.0)
    fov_angle = Column(Float, default=78.0) # Horizontal Field of View (degrees)
    heading_deg = Column(Float, default=45.0) # Camera facing direction
    range_meters = Column(Float, default=150.0)
    
    # Operation & health telemetry
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(Enum(CameraStatus), default=CameraStatus.OFFLINE, nullable=False)
    current_fps = Column(Float, default=0.0)
    target_fps = Column(Integer, default=15)
    latency_ms = Column(Float, default=0.0)
    resolution = Column(String(20), default="1280x720")
    codec = Column(String(20), default="h264")
    drop_rate_pct = Column(Float, default=0.0)
    
    # Night vision & enhancement settings
    night_mode_enabled = Column(Boolean, default=True)
    clahe_enhancement = Column(Boolean, default=True)

    # ONVIF & PTZ Control Configuration
    ptz_enabled = Column(Boolean, default=False, nullable=False)
    onvif_host = Column(String(100), nullable=True)
    onvif_port = Column(Integer, default=80, nullable=False)
    onvif_username = Column(String(100), nullable=True)
    onvif_password_encrypted = Column(String(255), nullable=True)
    onvif_profile_token = Column(String(100), nullable=True)
    
    last_frame_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    tripwires = relationship("Tripwire", back_populates="camera", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="camera", cascade="all, delete-orphan")
    recording_segments = relationship("RecordingSegment", back_populates="camera", cascade="all, delete-orphan")
    snapshots = relationship("TrackedSnapshot", back_populates="camera", cascade="all, delete-orphan")
    ptz_presets = relationship("PTZPreset", cascade="all, delete-orphan")
