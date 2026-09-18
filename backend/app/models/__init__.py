from app.core.database import Base
from app.models.user import User, UserRole
from app.models.camera import Camera, CameraStatus, StreamType, CameraRecordingMode
from app.models.recording import RecordingSegment, SegmentType
from app.models.snapshot import TrackedSnapshot
from app.models.zone import Zone, ZoneType, Tripwire, TripwireDirection
from app.models.rule import Rule, RuleSeverity, RuleEventType
from app.models.event import DetectionEvent, RuleEvent
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.models.evidence import Evidence, EvidenceType
from app.models.anpr import ANPRRecord, ANPRWatchlist, PlateWatchlistCategory, WatchlistPriority, PlateValidationStatus
from app.models.face import FaceRecord, FaceWatchlist, FaceIdentity, FaceWatchlistCategory, FaceMatchStatus, FaceWatchlistPriority
from app.models.audit import AuditLog
from app.models.integration import IntegrationConfig, IntegrationType, IntegrationStatus
from app.models.notification import Notification, NotificationRule, NotificationChannel, NotificationSeverity
from app.models.model_registry import AIModel, AIModelTask, AIModelStatus
from app.models.camera_group import CameraGroup
from app.models.camera_profile import CameraAIProfile
from app.models.cross_camera import (
    GlobalTrack,
    TrackObservation,
    CameraTopology,
    ReIDMatch,
    GlobalEntityType,
    IdentitySource
)
from app.models.ptz import PTZPreset, PTZLog, PTZStatusEnum, PTZModeEnum
from app.models.investigation import InvestigationCase, CaseFinding, CaseStatus, CasePriority

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Camera",
    "CameraStatus",
    "StreamType",
    "CameraRecordingMode",
    "CameraGroup",
    "RecordingSegment",
    "SegmentType",
    "TrackedSnapshot",
    "Zone",
    "ZoneType",
    "Tripwire",
    "TripwireDirection",
    "Rule",
    "RuleSeverity",
    "RuleEventType",
    "DetectionEvent",
    "RuleEvent",
    "Incident",
    "IncidentStatus",
    "IncidentSeverity",
    "Evidence",
    "EvidenceType",
    "ANPRRecord",
    "ANPRWatchlist",
    "PlateWatchlistCategory",
    "FaceRecord",
    "FaceWatchlist",
    "FaceWatchlistCategory",
    "AuditLog",
    "IntegrationConfig",
    "IntegrationType",
    "IntegrationStatus",
    "Notification",
    "NotificationRule",
    "NotificationChannel",
    "NotificationSeverity",
    "AIModel",
    "AIModelTask",
    "AIModelStatus",
    "CameraAIProfile",
    "GlobalTrack",
    "TrackObservation",
    "CameraTopology",
    "ReIDMatch",
    "GlobalEntityType",
    "IdentitySource",
    "PTZPreset",
    "PTZLog",
    "PTZStatusEnum",
    "PTZModeEnum",
    "InvestigationCase",
    "CaseFinding",
    "CaseStatus",
    "CasePriority"
]
