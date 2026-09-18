from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text, Index
from app.core.database import Base

class FaceWatchlistCategory(str, enum.Enum):
    WATCH = "WATCH"                   # Surveillance target
    ALERT = "ALERT"                   # High threat / Wanted criminal / Insurgent
    ALLOW = "ALLOW"                   # VIP / Authorized personnel / Diplomat
    CUSTOM = "CUSTOM"                 # Custom tagged group
    # Legacy aliases
    BLACK_LIST = "ALERT"
    PERSON_OF_INTEREST = "WATCH"
    VIP_AUTHORIZED = "ALLOW"
    MISSING_PERSON = "WATCH"

class FaceMatchStatus(str, enum.Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    UNCERTAIN = "UNCERTAIN"
    UNAVAILABLE = "UNAVAILABLE"

class FaceWatchlistPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class FaceIdentity(Base):
    __tablename__ = "face_identities"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False, index=True)
    external_id = Column(String(50), nullable=True, index=True) # Passport / National ID / Badge #
    unique_person_id = Column(String(50), nullable=True, index=True) # System Unique Person ID (e.g. PERSON-1001)
    category = Column(Enum(FaceWatchlistCategory), default=FaceWatchlistCategory.WATCH, nullable=False)
    priority = Column(Enum(FaceWatchlistPriority), default=FaceWatchlistPriority.HIGH, nullable=False)
    
    photo_path = Column(String(500), nullable=True)
    embedding_vector_json = Column(Text, nullable=False) # JSON list of floats (128D or 512D)
    quality_score = Column(Float, default=0.85, nullable=False)
    notes = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(50), default="SYSTEM", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def name(self) -> str:
        return self.full_name

    @name.setter
    def name(self, val: str):
        self.full_name = val

    @property
    def identifier(self) -> str:
        return self.external_id

    @identifier.setter
    def identifier(self, val: str):
        self.external_id = val

    @property
    def watchlist_category(self):
        return self.category

    @watchlist_category.setter
    def watchlist_category(self, val):
        self.category = val

    @property
    def watchlist_priority(self):
        return self.priority

    @watchlist_priority.setter
    def watchlist_priority(self, val):
        self.priority = val

    @property
    def reference_image_path(self) -> str:
        return self.photo_path

    @reference_image_path.setter
    def reference_image_path(self, val: str):
        self.photo_path = val

    @property
    def embeddings_json(self) -> str:
        return self.embedding_vector_json

    @embeddings_json.setter
    def embeddings_json(self, val: str):
        self.embedding_vector_json = val

# Backward-compatible alias
FaceWatchlist = FaceIdentity

class FaceRecord(Base):
    __tablename__ = "face_records"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, default=-1, nullable=False, index=True)
    unique_person_id = Column(String(50), nullable=True, index=True) # Persistent Unique Person ID (e.g. PERSON-1001)
    
    match_status = Column(Enum(FaceMatchStatus), default=FaceMatchStatus.UNKNOWN, nullable=False)
    identity_id = Column(Integer, ForeignKey("face_identities.id", ondelete="SET NULL"), nullable=True, index=True)
    matched_person_name = Column(String(100), nullable=True)
    similarity_score = Column(Float, default=0.0, nullable=False) # Cosine similarity (0.0 to 1.0)
    confidence = Column(Float, default=0.0, nullable=False) # Face detection confidence
    
    bbox_json = Column(String(200), nullable=True) # [x1, y1, x2, y2]
    landmarks_json = Column(String(500), nullable=True) # 5-point facial landmarks
    quality_score = Column(Float, default=0.0, nullable=False)
    
    is_matched = Column(Boolean, default=False, index=True, nullable=False)
    watchlist_category = Column(String(50), nullable=True)
    watchlist_priority = Column(String(50), nullable=True)
    
    crop_path = Column(String(500), nullable=True)
    full_frame_path = Column(String(500), nullable=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True)
    recording_segment_id = Column(Integer, ForeignKey("recording_segments.id", ondelete="SET NULL"), nullable=True)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    __table_args__ = (
        Index("ix_face_records_cam_time", "camera_id", "timestamp"),
        Index("ix_face_records_identity_time", "identity_id", "timestamp"),
    )

