from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text, Index
from app.core.database import Base

class PlateWatchlistCategory(str, enum.Enum):
    ALLOWLIST = "ALLOWLIST"           # Authorized / VIP / Convoy
    BLOCKLIST = "BLOCKLIST"           # Banned entry
    SUSPECT = "SUSPECT"               # High alert / Border watch
    STOLEN = "STOLEN"                 # Reported stolen vehicle
    CUSTOMS_FLAGGED = "CUSTOMS_FLAGGED" # Contraband / smuggling suspect
    DIPLOMATIC = "DIPLOMATIC"         # Diplomatic mission
    WANTED = "WANTED"                 # Wanted by law enforcement

class WatchlistPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PlateValidationStatus(str, enum.Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNCERTAIN = "UNCERTAIN"

class ANPRWatchlist(Base):
    __tablename__ = "anpr_watchlists"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(32), unique=True, index=True, nullable=False)
    category = Column(Enum(PlateWatchlistCategory), default=PlateWatchlistCategory.SUSPECT, nullable=False)
    priority = Column(Enum(WatchlistPriority), default=WatchlistPriority.HIGH, nullable=False)
    vehicle_model = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class ANPRRecord(Base):
    __tablename__ = "anpr_records"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, default=-1, nullable=False, index=True)
    
    # OCR & Text
    raw_text = Column(String(50), nullable=True)
    plate_number = Column(String(32), index=True, nullable=False) # normalized
    confidence = Column(Float, default=0.0, nullable=False)
    
    # Validation
    validation_status = Column(Enum(PlateValidationStatus), default=PlateValidationStatus.VALID, nullable=False)
    validation_format = Column(String(50), default="INDIAN_STANDARD", nullable=False)
    diagnostics = Column(String(255), nullable=True)

    # Vehicle Intelligence Attributes
    vehicle_type = Column(String(50), default="car", nullable=False) # car, motorcycle, bus, truck, bicycle
    vehicle_color = Column(String(50), nullable=True)
    vehicle_make = Column(String(50), nullable=True)
    vehicle_model = Column(String(50), nullable=True)
    is_stationary = Column(Boolean, default=False, nullable=False)
    dwell_duration_sec = Column(Float, default=0.0, nullable=False)
    
    # Watchlist Match Details
    is_matched = Column(Boolean, default=False, index=True, nullable=False)
    watchlist_category = Column(String(50), nullable=True)
    watchlist_priority = Column(String(50), nullable=True)
    
    # Evidence & Media References
    crop_path = Column(String(500), nullable=True)
    vehicle_crop_path = Column(String(500), nullable=True)
    full_frame_path = Column(String(500), nullable=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True)
    recording_segment_id = Column(Integer, ForeignKey("recording_segments.id", ondelete="SET NULL"), nullable=True)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    __table_args__ = (
        Index("ix_anpr_records_cam_time", "camera_id", "timestamp"),
        Index("ix_anpr_records_plate_time", "plate_number", "timestamp"),
    )

