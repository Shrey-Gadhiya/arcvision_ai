from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class GlobalEntityType(str, enum.Enum):
    PERSON = "PERSON"
    VEHICLE = "VEHICLE"
    OBJECT = "OBJECT"

class IdentitySource(str, enum.Enum):
    PLATE_MATCH = "PLATE_MATCH"
    FACE_MATCH = "FACE_MATCH"
    TOPOLOGY_TRANSITION = "TOPOLOGY_TRANSITION"
    REID_EMBEDDING = "REID_EMBEDDING"
    MANUAL = "MANUAL"

class GlobalTrack(Base):
    __tablename__ = "global_tracks"

    id = Column(Integer, primary_key=True, index=True)
    global_id = Column(String(50), unique=True, index=True, nullable=False) # e.g. GLOBAL-P-00421 or GLOBAL-V-00108
    entity_type = Column(Enum(GlobalEntityType), default=GlobalEntityType.PERSON, nullable=False, index=True)
    
    current_camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True, index=True)
    current_sector = Column(String(100), default="Sector North", nullable=False)
    
    # Associated Ground Truth Identifiers
    face_identity_id = Column(Integer, ForeignKey("face_identities.id", ondelete="SET NULL"), nullable=True, index=True)
    face_identity_name = Column(String(100), nullable=True)
    plate_number = Column(String(30), nullable=True, index=True)
    
    # Appearance & Metadata
    primary_color = Column(String(50), nullable=True)
    secondary_attributes_json = Column(Text, default="{}") # e.g. {"backpack": true, "vehicle_type": "sedan"}
    
    confidence = Column(Float, default=1.0, nullable=False)
    identity_source = Column(Enum(IdentitySource), default=IdentitySource.TOPOLOGY_TRANSITION, nullable=False)
    
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    notes = Column(String(255), nullable=True)

    # Relationships
    observations = relationship("TrackObservation", back_populates="global_track", cascade="all, delete-orphan", order_by="TrackObservation.timestamp")

class TrackObservation(Base):
    __tablename__ = "track_observations"

    id = Column(Integer, primary_key=True, index=True)
    global_track_id = Column(Integer, ForeignKey("global_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    local_track_id = Column(Integer, nullable=False, index=True)
    
    camera_name = Column(String(100), nullable=False)
    sector_name = Column(String(100), default="Perimeter Sector", nullable=False)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    duration_sec = Column(Float, default=0.0, nullable=False)
    
    bbox_json = Column(String(100), default="[0.0, 0.0, 1.0, 1.0]")
    crop_path = Column(String(500), nullable=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True)
    zones_json = Column(Text, default="[]") # Zones traversed at this camera
    
    # Relationships
    global_track = relationship("GlobalTrack", back_populates="observations")

class CameraTopology(Base):
    __tablename__ = "camera_topologies"

    id = Column(Integer, primary_key=True, index=True)
    from_camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    to_camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    
    distance_meters = Column(Float, default=50.0, nullable=False)
    min_travel_sec = Column(Float, default=2.0, nullable=False)
    max_travel_sec = Column(Float, default=120.0, nullable=False)
    
    direction = Column(String(50), default="BIDIRECTIONAL", nullable=False) # FORWARD, REVERSE, BIDIRECTIONAL
    sector = Column(String(100), default="Sector North - Main Path", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class ReIDMatch(Base):
    __tablename__ = "reid_matches"

    id = Column(Integer, primary_key=True, index=True)
    query_global_id = Column(String(50), nullable=False, index=True)
    candidate_observation_id = Column(Integer, ForeignKey("track_observations.id", ondelete="CASCADE"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    match_source = Column(Enum(IdentitySource), nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
