from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.user import UserRole
from app.models.camera import CameraStatus, StreamType, CameraRecordingMode
from app.models.zone import ZoneType, TripwireDirection
from app.models.rule import RuleSeverity, RuleEventType
from app.models.incident import IncidentStatus, IncidentSeverity
from app.models.evidence import EvidenceType

# Auth & User
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.OPERATOR

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# Camera
class CameraBase(BaseModel):
    name: str
    description: Optional[str] = None
    rtsp_url: str
    stream_type: StreamType = StreamType.SYNTHETIC
    group_name: str = "Perimeter North"
    location: str = "Sector 4 - Alpha Outpost"
    latitude: float = 26.8500
    longitude: float = 85.2000
    heading_deg: float = 45.0
    fov_angle: float = 78.0
    target_fps: int = 15
    detect_stream_url: Optional[str] = None
    record_stream_url: Optional[str] = None
    audio_stream_url: Optional[str] = None
    recording_mode: CameraRecordingMode = CameraRecordingMode.CONTINUOUS
    retention_days: int = 7
    retention_events_days: int = 30
    active_profile: str = "NORMAL"
    motion_detection_enabled: bool = True
    anpr_enabled: bool = True
    night_mode_enabled: bool = True

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rtsp_url: Optional[str] = None
    stream_type: Optional[StreamType] = None
    group_name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    heading_deg: Optional[float] = None
    fov_angle: Optional[float] = None
    target_fps: Optional[int] = None
    detect_stream_url: Optional[str] = None
    record_stream_url: Optional[str] = None
    audio_stream_url: Optional[str] = None
    recording_mode: Optional[CameraRecordingMode] = None
    retention_days: Optional[int] = None
    retention_events_days: Optional[int] = None
    active_profile: Optional[str] = None
    motion_detection_enabled: Optional[bool] = None
    anpr_enabled: Optional[bool] = None
    night_mode_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

class CameraResponse(CameraBase):
    id: int
    is_active: bool
    status: CameraStatus
    current_fps: float
    latency_ms: float
    resolution: str
    codec: str
    drop_rate_pct: float
    created_at: datetime
    class Config:
        from_attributes = True

# Zones & Tripwires
class ZoneCreate(BaseModel):
    camera_id: int
    name: str
    zone_type: ZoneType = ZoneType.RESTRICTED
    points_json: str # List of dicts [{"x": 0.1, "y": 0.2}, ...]
    color_hex: str = "#EF4444"
    loitering_time_sec: int = 15

class ZoneResponse(BaseModel):
    id: int
    camera_id: int
    name: str
    zone_type: ZoneType
    points_json: str
    color_hex: str
    loitering_time_sec: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class TripwireCreate(BaseModel):
    camera_id: int
    name: str
    line_json: str # {"start": {"x": 0.1, "y": 0.5}, "end": {"x": 0.9, "y": 0.5}}
    direction: TripwireDirection = TripwireDirection.A_TO_B
    color_hex: str = "#F59E0B"

class TripwireResponse(BaseModel):
    id: int
    camera_id: int
    name: str
    line_json: str
    direction: TripwireDirection
    color_hex: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# Rules
class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: RuleEventType
    severity: RuleSeverity = RuleSeverity.HIGH
    camera_ids_json: str = "[]"
    conditions_json: str = "{}"
    schedule_json: str = '{"always": true}'
    cooldown_seconds: int = 30

class RuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    event_type: RuleEventType
    severity: RuleSeverity
    camera_ids_json: str
    conditions_json: str
    schedule_json: str
    cooldown_seconds: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[RuleEventType] = None
    severity: Optional[RuleSeverity] = None
    camera_ids_json: Optional[str] = None
    conditions_json: Optional[str] = None
    schedule_json: Optional[str] = None
    cooldown_seconds: Optional[int] = None
    is_active: Optional[bool] = None

class AnalyticsStatusResponse(BaseModel):
    engine_name: str
    total_analyzers: int
    rule_analyzers_status: str
    analyzers: Dict[str, Any]
    ml_action_model: Dict[str, Any]

# Incidents
class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    resolution_reason: Optional[str] = None
    resolution_notes: Optional[str] = None
    note: Optional[str] = None

class IncidentTransitionRequest(BaseModel):
    target_status: IncidentStatus
    reason: Optional[str] = None
    note: Optional[str] = None

class IncidentAssignRequest(BaseModel):
    assigned_to: str
    note: Optional[str] = None

class IncidentAddNote(BaseModel):
    note: str

class IncidentResponse(BaseModel):
    id: int
    incident_code: str
    title: str
    summary: str
    incident_type: str
    camera_id: int
    track_id: Optional[int] = None
    severity: IncidentSeverity
    status: IncidentStatus
    threat_score: float
    location_name: str
    correlated_event_ids: str
    tags_json: str
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    detected_at: datetime
    triaged_at: Optional[datetime] = None
    triaged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    resolution_reason: Optional[str] = None
    resolution_notes: Optional[str] = None
    transition_history_json: str = "[]"
    operator_notes_json: str = "[]"
    class Config:
        from_attributes = True

# Evidence
class EvidenceResponse(BaseModel):
    id: int
    incident_id: Optional[int] = None
    camera_id: int
    file_type: EvidenceType
    file_path: str
    file_size_bytes: int
    sha256_hash: str
    metadata_json: str
    created_at: datetime
    class Config:
        from_attributes = True

# ANPR
class ANPRWatchlistCreate(BaseModel):
    plate_number: str
    category: str = "SUSPECT"
    vehicle_model: Optional[str] = None
    notes: Optional[str] = None

class ANPRRecordResponse(BaseModel):
    id: int
    camera_id: int
    plate_number: str
    vehicle_type: str
    confidence: float
    is_matched: bool
    watchlist_category: Optional[str] = None
    crop_path: Optional[str] = None
    full_frame_path: Optional[str] = None
    timestamp: datetime
    class Config:
        from_attributes = True

# Face
class FaceWatchlistCreate(BaseModel):
    full_name: str
    national_id: Optional[str] = None
    category: str = "BLACK_LIST"
    photo_path: str
    notes: Optional[str] = None

class FaceRecordResponse(BaseModel):
    id: int
    camera_id: int
    track_id: Optional[int] = None
    is_matched: bool
    matched_person_id: Optional[int] = None
    matched_person_name: Optional[str] = None
    similarity_score: float
    confidence: float
    crop_path: Optional[str] = None
    timestamp: datetime
    class Config:
        from_attributes = True

# Audit
class AuditLogResponse(BaseModel):
    id: int
    username: str
    user_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details_json: str
    ip_address: str
    timestamp: datetime
    class Config:
        from_attributes = True

# Camera Group
class CameraGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sector: str = "General Sector"
    tags_json: str = "[]"

class CameraGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sector: str
    tags_json: str
    created_at: datetime
    class Config:
        from_attributes = True

# Integration
class IntegrationConfigCreate(BaseModel):
    name: str
    integration_type: str
    endpoint_url: Optional[str] = None
    port: Optional[int] = None
    topic: Optional[str] = None
    auth_secret: Optional[str] = None
    headers_json: str = "{}"
    qos: int = 1
    tls_enabled: bool = False
    retry_count: int = 3
    status: str = "INACTIVE"

class IntegrationConfigUpdate(BaseModel):
    name: Optional[str] = None
    endpoint_url: Optional[str] = None
    port: Optional[int] = None
    topic: Optional[str] = None
    auth_secret: Optional[str] = None
    headers_json: Optional[str] = None
    qos: Optional[int] = None
    tls_enabled: Optional[bool] = None
    retry_count: Optional[int] = None
    status: Optional[str] = None

class IntegrationConfigResponse(BaseModel):
    id: int
    name: str
    integration_type: str
    endpoint_url: Optional[str] = None
    port: Optional[int] = None
    topic: Optional[str] = None
    masked_secret: Optional[str] = None
    headers_json: str
    qos: int
    tls_enabled: bool
    retry_count: int
    status: str
    last_dispatched_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Notification
class NotificationRuleCreate(BaseModel):
    name: str
    channel: str = "IN_APP"
    severity_filter_json: str = '["HIGH", "CRITICAL"]'
    camera_ids_json: str = "[]"
    event_types_json: str = "[]"
    cooldown_seconds: int = 60
    integration_id: Optional[int] = None
    is_active: bool = True

class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    severity_filter_json: Optional[str] = None
    camera_ids_json: Optional[str] = None
    event_types_json: Optional[str] = None
    cooldown_seconds: Optional[int] = None
    integration_id: Optional[int] = None
    is_active: Optional[bool] = None

class NotificationRuleResponse(BaseModel):
    id: int
    name: str
    channel: str
    severity_filter_json: str
    camera_ids_json: str
    event_types_json: str
    cooldown_seconds: int
    integration_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    channel: str
    camera_id: Optional[int] = None
    incident_id: Optional[int] = None
    is_read: bool
    dispatched_at: datetime
    metadata_json: str
    class Config:
        from_attributes = True

# AI Model Registry
class AIModelCreate(BaseModel):
    name: str
    version: str = "1.0.0"
    task: str = "DETECTION"
    provider: str = "Ultralytics / ONNX"
    model_path: str
    format: str = "PyTorch/ONNX"
    input_resolution: str = "640x640"
    classes_json: str = "[]"
    device: str = "CPU"
    status: str = "STANDBY"

class AIModelUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    provider: Optional[str] = None
    model_path: Optional[str] = None
    format: Optional[str] = None
    input_resolution: Optional[str] = None
    classes_json: Optional[str] = None
    device: Optional[str] = None
    status: Optional[str] = None

class AIModelResponse(BaseModel):
    id: int
    name: str
    version: str
    task: str
    provider: str
    model_path: str
    format: str
    input_resolution: str
    classes_json: str
    device: str
    status: str
    inference_latency_ms: float
    inference_fps: float
    memory_mb: float
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Camera AI Profiles
class CameraAIProfileCreate(BaseModel):
    camera_id: int
    person_detection: bool = True
    vehicle_detection: bool = True
    anpr: bool = True
    face_recognition: bool = True
    pose_estimation: bool = False
    fall_detection: bool = True
    fire_smoke: bool = True
    weapon_detection: bool = False
    action_recognition: bool = False
    crowd_analysis: bool = True
    behavior_analytics: bool = True
    attribute_analysis: bool = False
    person_interval_frames: int = 2
    vehicle_interval_frames: int = 2
    pose_interval_frames: int = 3
    fall_interval_frames: int = 2
    fire_smoke_interval_frames: int = 5
    weapon_interval_frames: int = 5
    action_interval_frames: int = 4
    crowd_interval_frames: int = 5
    attribute_interval_frames: int = 6
    detection_threshold: float = 0.35
    face_threshold: float = 0.50
    anpr_threshold: float = 0.45
    pose_threshold: float = 0.40
    fall_threshold: float = 0.65
    fire_smoke_threshold: float = 0.40
    weapon_threshold: float = 0.50
    action_threshold: float = 0.60
    crowd_density_threshold: int = 8
    fire_smoke_persistence_sec: float = 1.5
    fall_persistence_sec: float = 2.0
    weapon_persistence_sec: float = 0.5
    crowd_persistence_sec: float = 5.0
    notes: Optional[str] = None

class CameraAIProfileUpdate(BaseModel):
    person_detection: Optional[bool] = None
    vehicle_detection: Optional[bool] = None
    anpr: Optional[bool] = None
    face_recognition: Optional[bool] = None
    pose_estimation: Optional[bool] = None
    fall_detection: Optional[bool] = None
    fire_smoke: Optional[bool] = None
    weapon_detection: Optional[bool] = None
    action_recognition: Optional[bool] = None
    crowd_analysis: Optional[bool] = None
    behavior_analytics: Optional[bool] = None
    attribute_analysis: Optional[bool] = None
    person_interval_frames: Optional[int] = None
    vehicle_interval_frames: Optional[int] = None
    pose_interval_frames: Optional[int] = None
    fall_interval_frames: Optional[int] = None
    fire_smoke_interval_frames: Optional[int] = None
    weapon_interval_frames: Optional[int] = None
    action_interval_frames: Optional[int] = None
    crowd_interval_frames: Optional[int] = None
    attribute_interval_frames: Optional[int] = None
    detection_threshold: Optional[float] = None
    face_threshold: Optional[float] = None
    anpr_threshold: Optional[float] = None
    pose_threshold: Optional[float] = None
    fall_threshold: Optional[float] = None
    fire_smoke_threshold: Optional[float] = None
    weapon_threshold: Optional[float] = None
    action_threshold: Optional[float] = None
    crowd_density_threshold: Optional[int] = None
    fire_smoke_persistence_sec: Optional[float] = None
    fall_persistence_sec: Optional[float] = None
    weapon_persistence_sec: Optional[float] = None
    crowd_persistence_sec: Optional[float] = None
    notes: Optional[str] = None

class CameraAIProfileResponse(BaseModel):
    id: int
    camera_id: int
    person_detection: bool
    vehicle_detection: bool
    anpr: bool
    face_recognition: bool
    pose_estimation: bool
    fall_detection: bool
    fire_smoke: bool
    weapon_detection: bool
    action_recognition: bool
    crowd_analysis: bool
    behavior_analytics: bool
    attribute_analysis: bool
    person_interval_frames: int
    vehicle_interval_frames: int
    pose_interval_frames: int
    fall_interval_frames: int
    fire_smoke_interval_frames: int
    weapon_interval_frames: int
    action_interval_frames: int
    crowd_interval_frames: int
    attribute_interval_frames: int
    detection_threshold: float
    face_threshold: float
    anpr_threshold: float
    pose_threshold: float
    fall_threshold: float
    fire_smoke_threshold: float
    weapon_threshold: float
    action_threshold: float
    crowd_density_threshold: int
    fire_smoke_persistence_sec: float
    fall_persistence_sec: float
    weapon_persistence_sec: float
    crowd_persistence_sec: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class PerceptionTelemetryResponse(BaseModel):
    system_cpu_utilization_pct: float
    process_memory_mb: float
    ai_models_memory_mb: float
    active_adapters_count: int
    total_adapters_count: int
    adapters: List[Dict[str, Any]]

# Cross-Camera & Global Entity Tracking Schemas
class TrackObservationResponse(BaseModel):
    id: int
    global_track_id: int
    camera_id: int
    local_track_id: int
    camera_name: str
    sector_name: str
    timestamp: datetime
    duration_sec: float
    bbox_json: str
    crop_path: Optional[str] = None
    evidence_id: Optional[int] = None
    zones_json: str
    class Config:
        from_attributes = True

class GlobalTrackResponse(BaseModel):
    id: int
    global_id: str
    entity_type: str
    current_camera_id: Optional[int] = None
    current_sector: str
    face_identity_id: Optional[int] = None
    face_identity_name: Optional[str] = None
    plate_number: Optional[str] = None
    primary_color: Optional[str] = None
    confidence: float
    identity_source: str
    first_seen: datetime
    last_seen: datetime
    is_active: bool
    notes: Optional[str] = None
    class Config:
        from_attributes = True

class GlobalTrackDetailResponse(GlobalTrackResponse):
    observations: List[TrackObservationResponse] = []
    journey_hops_count: int = 0
    route_cameras: List[str] = []

class CameraTopologyCreate(BaseModel):
    from_camera_id: int
    to_camera_id: int
    distance_meters: float = 50.0
    min_travel_sec: float = 2.0
    max_travel_sec: float = 120.0
    direction: str = "BIDIRECTIONAL"
    sector: str = "Sector North - Perimeter"
    is_active: bool = True

class CameraTopologyResponse(BaseModel):
    id: int
    from_camera_id: int
    to_camera_id: int
    distance_meters: float
    min_travel_sec: float
    max_travel_sec: float
    direction: str
    sector: str
    is_active: bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class CrossCameraSearchRequest(BaseModel):
    global_id: Optional[str] = None
    entity_type: Optional[str] = None
    plate_number: Optional[str] = None
    face_identity_name: Optional[str] = None
    camera_id: Optional[int] = None
    sector_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50

# Phase K: ONVIF & PTZ Schemas
class PTZMoveRequest(BaseModel):
    pan_speed: float = 0.0 # -1.0 (Left) to +1.0 (Right)
    tilt_speed: float = 0.0 # -1.0 (Down) to +1.0 (Up)
    zoom_speed: float = 0.0 # -1.0 (Out) to +1.0 (In)
    speed: float = 0.5 # 0.1 to 1.0 multiplier

class PTZRelativeMoveRequest(BaseModel):
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 0.0
    speed: float = 0.5

class PTZPresetCreate(BaseModel):
    name: str

class PTZPresetResponse(BaseModel):
    id: int
    camera_id: int
    preset_token: str
    name: str
    pan: float
    tilt: float
    zoom: float
    is_home: bool = False
    created_at: Optional[str] = None
    class Config:
        from_attributes = True

class PTZStatusResponse(BaseModel):
    camera_id: int
    camera_name: Optional[str] = None
    ptz_enabled: bool = False
    onvif_host: str = "NOT_CONFIGURED"
    onvif_port: int = 80
    status: str
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 1.0
    is_moving: bool = False
    last_action: Optional[str] = None
    error_message: Optional[str] = None

class PTZCapabilitiesResponse(BaseModel):
    supports_continuous_move: bool = True
    supports_relative_move: bool = True
    supports_absolute_move: bool = False
    supports_zoom: bool = True
    supports_presets: bool = True
    supports_home_position: bool = True
    supports_speed_control: bool = True
    max_presets: int = 128
    pan_range: List[float] = [-1.0, 1.0]
    tilt_range: List[float] = [-1.0, 1.0]
    zoom_range: List[float] = [0.0, 1.0]

class CameraGeospatialUpdate(BaseModel):
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    fov_angle: Optional[float] = None
    heading_deg: Optional[float] = None
    range_meters: Optional[float] = None
    onvif_host: Optional[str] = None
    onvif_port: Optional[int] = None
    onvif_username: Optional[str] = None
    onvif_password: Optional[str] = None
    ptz_enabled: Optional[bool] = None

# System Telemetry & Observability
class SystemHealthResponse(BaseModel):
    cpu_utilization_pct: float
    memory_used_mb: float
    memory_total_mb: float
    memory_utilization_pct: float
    disk_used_gb: float
    disk_total_gb: float
    disk_utilization_pct: float
    active_stream_workers: int
    online_cameras_count: int
    total_cameras_count: int
    processing_fps_aggregate: float
    db_status: str
    active_inference_device: str
    uptime_seconds: float
    timestamp: datetime

# Phase E: Recordings & VMS Segments
class RecordingSegmentResponse(BaseModel):
    id: int
    camera_id: int
    start_time: datetime
    end_time: datetime
    duration_sec: float
    file_path: str
    file_size_bytes: int
    segment_type: str
    motion_score: float
    has_objects: bool
    objects_detected: List[str] = []
    sha256_hash: Optional[str] = None
    is_protected: bool = False
    codec: str = "H.264 / MP4"
    resolution: str = "1280x720"
    created_at: datetime
    class Config:
        from_attributes = True

class RecordingListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[RecordingSegmentResponse]

class RecordingProtectRequest(BaseModel):
    is_protected: bool = True
    reason: Optional[str] = "Forensic Lock"

class RecordingCorrelationResponse(BaseModel):
    camera_id: int
    query_window: Dict[str, str]
    total_segments: int
    segments: List[RecordingSegmentResponse]
    pre_event_segment: Optional[RecordingSegmentResponse] = None
    event_segments: List[RecordingSegmentResponse] = []
    post_event_segment: Optional[RecordingSegmentResponse] = None

# Phase E & L: Investigation Search, NL Query Parsing & Case Dossiers
class InvestigationSearchFilter(BaseModel):
    camera_id: Optional[int] = None
    object_class: Optional[str] = None
    track_id: Optional[int] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    zone_id: Optional[int] = None
    min_confidence: Optional[float] = None
    min_dwell_sec: Optional[float] = None
    color: Optional[str] = None
    plate_number: Optional[str] = None
    face_name: Optional[str] = None
    query_text: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

class InvestigationSearchResultItem(BaseModel):
    id: str
    result_type: str  # "DETECTION", "INCIDENT", "RULE_EVENT", "ANPR", "FACE", "GLOBAL_TRACK", "EVIDENCE"
    timestamp: datetime
    camera_id: int
    camera_name: Optional[str] = None
    object_class: Optional[str] = None
    track_id: Optional[int] = None
    confidence: Optional[float] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    thumbnail_url: Optional[str] = None
    details: Dict[str, Any] = {}
    linked_recording: Optional[Dict[str, Any]] = None
    linked_evidence_id: Optional[int] = None
    match_score: Optional[float] = 1.0
    matched_reasons: List[str] = []
    sector: Optional[str] = None
    zone_name: Optional[str] = None
    global_track_id: Optional[int] = None
    attributes_detected: List[str] = []

class InvestigationSearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[InvestigationSearchResultItem]

# Phase L: Natural Language Semantic Search Schemas
class ParsedSemanticQuery(BaseModel):
    raw_query: str
    object_classes: List[str] = []
    colors: List[str] = []
    attributes: List[str] = []
    locations: List[str] = []
    camera_ids: List[int] = []
    plate_numbers: List[str] = []
    person_names: List[str] = []
    incident_types: List[str] = []
    severities: List[str] = []
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    temporal_expression: Optional[str] = None
    action_terms: List[str] = []
    explanation: str
    parser_confidence: float = 1.0

class NLSearchRequest(BaseModel):
    query: str
    min_confidence: Optional[float] = 0.2
    limit: int = 50
    offset: int = 0

class NLSearchResponse(BaseModel):
    parsed_query: ParsedSemanticQuery
    total: int
    limit: int
    offset: int
    items: List[InvestigationSearchResultItem]

# Phase L: Investigation Case & Dossier Schemas
class CaseFindingCreate(BaseModel):
    item_type: str  # "INCIDENT", "DETECTION", "GLOBAL_TRACK", "ANPR", "FACE", "EVIDENCE", "RECORDING", "SNAPSHOT", "NOTE"
    reference_id: Optional[str] = None
    camera_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    title: str
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}
    thumbnail_url: Optional[str] = None

class CaseFindingResponse(BaseModel):
    id: int
    case_id: int
    item_type: str
    reference_id: Optional[str] = None
    camera_id: Optional[int] = None
    camera_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    title: str
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}
    thumbnail_url: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class InvestigationCaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "MEDIUM"
    lead_investigator: Optional[str] = "Lead Investigator"
    hypothesis: Optional[str] = None
    tags: List[str] = []

class InvestigationCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    lead_investigator: Optional[str] = None
    hypothesis: Optional[str] = None
    tags: Optional[List[str]] = None

class InvestigationCaseResponse(BaseModel):
    id: int
    case_number: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    lead_investigator: str
    hypothesis: Optional[str] = None
    tags: List[str] = []
    findings_count: int = 0
    findings: List[CaseFindingResponse] = []
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class InvestigationCaseListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[InvestigationCaseResponse]

class InvestigationTimelineEvent(BaseModel):
    id: str
    timestamp: datetime
    camera_id: Optional[int] = None
    camera_name: Optional[str] = None
    event_type: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    severity: Optional[str] = None
    metadata: Dict[str, Any] = {}

class CaseTimelineResponse(BaseModel):
    case_id: int
    case_number: str
    title: str
    total_events: int
    camera_sequence: List[Dict[str, Any]] = []
    events: List[InvestigationTimelineEvent] = []

class CaseExportResponse(BaseModel):
    case: InvestigationCaseResponse
    timeline: List[InvestigationTimelineEvent] = []
    summary_statistics: Dict[str, Any] = {}
    html_report: str


# Phase E: Evidence Package
class EvidencePackageManifestFile(BaseModel):
    path: str
    file_type: str
    file_size_bytes: int
    sha256_hash: str

class EvidencePackageManifest(BaseModel):
    incident_id: int
    incident_code: str
    camera_id: int
    camera_name: str
    generated_at: str
    generated_by: str
    summary: str
    threat_score: float
    total_files: int
    files: List[EvidencePackageManifestFile]
    manifest_signature: str

class EvidencePackageExportResponse(BaseModel):
    package_filename: str
    download_url: str
    file_size_bytes: int
    sha256_hash: str
    total_files: int
    is_protected: bool
    manifest: EvidencePackageManifest

class EvidencePackageVerifyRequest(BaseModel):
    package_filename: str

class EvidencePackageVerifyResponse(BaseModel):
    package_filename: str
    is_valid: bool
    status: str
    verified_files_count: int
    tampered_files: List[str] = []
    recorded_manifest_hash: str
    calculated_manifest_hash: str

# ============================================================================
# Phase F: ANPR & Vehicle Intelligence Schemas
# ============================================================================

class ANPRWatchlistCreate(BaseModel):
    plate_number: str
    category: str = "SUSPECT"
    priority: str = "HIGH"
    vehicle_model: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

class ANPRWatchlistUpdate(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = None
    vehicle_model: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ANPRWatchlistResponse(BaseModel):
    id: int
    plate_number: str
    category: str
    priority: str
    vehicle_model: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class ANPRRecordResponse(BaseModel):
    id: int
    camera_id: int
    track_id: int
    raw_text: Optional[str] = None
    plate_number: str
    confidence: float
    validation_status: str
    validation_format: str
    diagnostics: Optional[str] = None
    vehicle_type: str
    vehicle_color: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    is_stationary: bool
    dwell_duration_sec: float
    is_matched: bool
    watchlist_category: Optional[str] = None
    watchlist_priority: Optional[str] = None
    crop_path: Optional[str] = None
    vehicle_crop_path: Optional[str] = None
    full_frame_path: Optional[str] = None
    evidence_id: Optional[int] = None
    recording_segment_id: Optional[int] = None
    timestamp: datetime
    class Config:
        from_attributes = True

class ANPRRecordPaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ANPRRecordResponse]

class PlateSearchQuery(BaseModel):
    plate_number: Optional[str] = None
    camera_id: Optional[int] = None
    vehicle_type: Optional[str] = None
    min_confidence: Optional[float] = None
    is_matched: Optional[bool] = None
    validation_status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

class PlateQueryResult(BaseModel):
    plate_number: str
    normalized_plate: str
    validation_status: str
    validation_format: str
    is_flagged: bool
    watchlist_info: Optional[ANPRWatchlistResponse] = None
    sightings_count: int
    history: List[ANPRRecordResponse]

class VehicleIntelligenceStats(BaseModel):
    total_sightings: int
    unique_plates: int
    watchlist_hits: int
    stationary_vehicles_count: int
    vehicle_class_distribution: Dict[str, int]
    top_seen_plates: List[Dict[str, Any]]
    recent_flagged_vehicles: List[ANPRRecordResponse]

class ANPRStatusResponse(BaseModel):
    engine_name: str
    detector_adapter: str
    detector_status: str
    ocr_adapter: str
    ocr_status: str
    ocr_details: str
    active_cameras_count: int
    total_sightings_today: int
    validation_capabilities: List[str]

class ANPRCaptureRequest(BaseModel):
    image_base64: str
    camera_id: Optional[int] = 1
    camera_name: Optional[str] = "Manual Forensic Terminal"
    notes: Optional[str] = None

class ANPRCaptureResponse(BaseModel):
    success: bool
    record_id: Optional[int] = None
    plate_number: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0
    ocr_confidence: float = 0.0
    validation_status: Optional[str] = None
    validation_format: Optional[str] = None
    diagnostics: Optional[str] = None
    is_matched: bool = False
    watchlist_category: Optional[str] = None
    watchlist_priority: Optional[str] = None
    plate_crop_url: Optional[str] = None
    full_frame_url: Optional[str] = None
    annotated_frame_url: Optional[str] = None
    plate_box: Optional[List[int]] = None
    error: Optional[str] = None

# ==========================================
# FACE INTELLIGENCE SCHEMAS (PHASE G)
# ==========================================

class FaceIdentityCreate(BaseModel):
    name: str
    identifier: Optional[str] = None
    notes: Optional[str] = None
    watchlist_category: Optional[str] = "CUSTOM"
    watchlist_priority: Optional[str] = "LOW"
    is_active: bool = True

class FaceIdentityUpdate(BaseModel):
    name: Optional[str] = None
    identifier: Optional[str] = None
    notes: Optional[str] = None
    watchlist_category: Optional[str] = None
    watchlist_priority: Optional[str] = None
    is_active: Optional[bool] = None

class FaceIdentityResponse(BaseModel):
    id: int
    name: str
    identifier: Optional[str] = None
    unique_person_id: Optional[str] = None
    notes: Optional[str] = None
    watchlist_category: str
    watchlist_priority: str
    is_active: bool
    embedding_count: int = 0
    reference_image_path: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class FaceEnrollmentRequest(BaseModel):
    name: str
    identifier: Optional[str] = None
    watchlist_category: Optional[str] = "CUSTOM"
    watchlist_priority: Optional[str] = "LOW"
    notes: Optional[str] = None
    image_base64: str

class FaceEnrollmentResponse(BaseModel):
    success: bool
    identity_id: Optional[int] = None
    name: Optional[str] = None
    quality_score: float = 0.0
    sharpness_score: float = 0.0
    diagnostics: str
    embedding_generated: bool
    error: Optional[str] = None

class FaceRecordResponse(BaseModel):
    id: int
    camera_id: int
    track_id: Optional[int] = None
    unique_person_id: Optional[str] = None
    identity_id: Optional[int] = None
    identity_name: Optional[str] = None
    match_status: str
    similarity_score: float
    recognition_threshold: float
    watchlist_category: Optional[str] = None
    watchlist_priority: Optional[str] = None
    bbox_x1: Optional[int] = None
    bbox_y1: Optional[int] = None
    bbox_x2: Optional[int] = None
    bbox_y2: Optional[int] = None
    quality_score: float
    sharpness_score: float
    diagnostics: Optional[str] = None
    crop_path: Optional[str] = None
    full_frame_path: Optional[str] = None
    evidence_id: Optional[int] = None
    recording_segment_id: Optional[int] = None
    detector_model: Optional[str] = None
    embedding_model: Optional[str] = None
    timestamp: datetime
    class Config:
        from_attributes = True

class FaceRecordPaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[FaceRecordResponse]

class FaceSearchQuery(BaseModel):
    identity_id: Optional[int] = None
    unique_person_id: Optional[str] = None
    name: Optional[str] = None
    match_status: Optional[str] = None
    watchlist_category: Optional[str] = None
    camera_id: Optional[int] = None
    min_similarity: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

class FaceStatusResponse(BaseModel):
    engine_name: str
    detector_adapter: str
    detector_status: str
    detector_fps: float
    detector_latency_ms: float
    detector_device: str
    embedding_adapter: str
    embedding_status: str
    embedding_dimension: int
    embedding_latency_ms: float
    total_identities: int
    active_watchlist_identities: int
    total_sightings_today: int
    hardware_target: str



