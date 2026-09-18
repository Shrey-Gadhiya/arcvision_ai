export type UserRole = 'ADMIN' | 'COMMANDER' | 'OPERATOR' | 'INVESTIGATOR' | 'VIEWER' | 'AUDITOR';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type CameraStatus = 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'CONNECTING';
export type StreamType = 'RTSP' | 'FILE' | 'SYNTHETIC' | 'WEBCAM';
export type CameraRecordingMode = 'CONTINUOUS' | 'MOTION_ONLY' | 'EVENT_ONLY' | 'DISABLED';

export interface Camera {
  id: number;
  name: string;
  description?: string;
  rtsp_url: string;
  detect_stream_url?: string;
  record_stream_url?: string;
  audio_stream_url?: string;
  stream_type: StreamType;
  group_name: string;
  location: string;
  latitude: number;
  longitude: number;
  heading_deg: number;
  fov_angle: number;
  target_fps: number;
  current_fps: number;
  latency_ms: number;
  status: CameraStatus;
  is_active: boolean;
  recording_mode: CameraRecordingMode;
  retention_days: number;
  retention_events_days: number;
  active_profile: string;
  motion_detection_enabled: boolean;
  anpr_enabled?: boolean;
  night_mode_enabled?: boolean;
  // Phase K: PTZ & Geospatial
  ptz_enabled?: boolean;
  altitude_m?: number;
  range_meters?: number;
  onvif_host?: string;
  onvif_port?: number;
  created_at: string;
}

export type SegmentType = 'CONTINUOUS' | 'MOTION' | 'EVENT';

export interface RecordingSegment {
  id: number;
  camera_id: number;
  start_time: string;
  end_time: string;
  duration_sec: number;
  file_path: string;
  file_size_bytes: number;
  segment_type: SegmentType;
  motion_score: number;
  has_objects: boolean;
  objects_detected: string[];
  sha256_hash: string;
  is_protected?: boolean;
  codec?: string;
  resolution?: string;
  created_at?: string;
}

export interface TrackedSnapshot {
  id: number;
  camera_id: number;
  camera_name?: string;
  track_id: number;
  object_class: string;
  confidence: number;
  clean_image_path: string;
  annotated_image_path: string;
  crop_image_path: string;
  box?: number[];
  quality_score?: number;
  timestamp: string;
}

export interface StorageCategoryTelemetry {
  bytes: number;
  count: number;
}

export interface CameraStorageTelemetry {
  camera_id: number;
  camera_name: string;
  group_name: string;
  recording_mode: string;
  retention_days: number;
  retention_events_days: number;
  recording_bytes: number;
  recording_count: number;
  snapshot_bytes: number;
  snapshot_count: number;
  total_bytes: number;
}

export interface StorageTelemetry {
  disk_total_bytes: number;
  disk_used_bytes: number;
  disk_free_bytes: number;
  disk_used_percent: number;
  arc_vision_total_bytes: number;
  categories: {
    recordings: StorageCategoryTelemetry;
    snapshots: StorageCategoryTelemetry;
    evidence: StorageCategoryTelemetry;
    database?: StorageCategoryTelemetry;
  };
  protected_evidence?: {
    count: number;
    bytes: number;
  };
  oldest_recording_time?: string;
  newest_recording_time?: string;
  warning_level?: string;
  warning_message?: string;
  per_camera: CameraStorageTelemetry[];
}

export interface InvestigationSearchResultItem {
  id: string;
  result_type: 'DETECTION' | 'INCIDENT' | 'RULE_EVENT' | 'ANPR' | 'FACE' | 'GLOBAL_TRACK' | 'EVIDENCE';
  timestamp: string;
  camera_id: number;
  camera_name?: string;
  object_class?: string;
  track_id?: number;
  confidence?: number;
  event_type?: string;
  severity?: string;
  thumbnail_url?: string;
  details: Record<string, any>;
  linked_recording?: {
    id: number;
    file_path: string;
    start_time: string;
    end_time: string;
    duration_sec: number;
  };
  linked_evidence_id?: number;
  match_score?: number;
  matched_reasons?: string[];
  sector?: string;
  zone_name?: string;
  global_track_id?: number;
  attributes_detected?: string[];
}

export interface EvidencePackageManifestFile {
  path: string;
  file_type: string;
  file_size_bytes: number;
  sha256_hash: string;
}

export interface EvidencePackageManifest {
  incident_id: number;
  incident_code: string;
  camera_id: number;
  camera_name: string;
  generated_at: string;
  generated_by: string;
  summary: string;
  threat_score: number;
  total_files: number;
  files: EvidencePackageManifestFile[];
  manifest_signature: string;
}

export interface EvidencePackageExportResponse {
  package_filename: string;
  download_url: string;
  file_size_bytes: number;
  sha256_hash: string;
  total_files: number;
  is_protected: boolean;
  manifest: EvidencePackageManifest;
}

export interface EvidencePackageVerifyResponse {
  package_filename: string;
  is_valid: boolean;
  status: string;
  verified_files_count: number;
  tampered_files: string[];
  recorded_manifest_hash: string;
  calculated_manifest_hash: string;
}

export type ZoneType = 'RESTRICTED' | 'BUFFER' | 'CHECKPOINT' | 'EXCLUSION';
export interface ZonePoint {
  x: number;
  y: number;
}

export interface Zone {
  id: number;
  camera_id: number;
  name: string;
  zone_type: ZoneType;
  points_json: string;
  color_hex: string;
  loitering_time_sec: number;
  is_active: boolean;
  created_at: string;
}

export type TripwireDirection = 'BIDIRECTIONAL' | 'A_TO_B' | 'B_TO_A';
export interface Tripwire {
  id: number;
  camera_id: number;
  name: string;
  line_json: string;
  direction: TripwireDirection;
  color_hex: string;
  is_active: boolean;
  created_at: string;
}

export type RuleSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type RuleEventType =
  | 'PERIMETER_BREACH'
  | 'ZONE_INTRUSION'
  | 'LOITERING'
  | 'VIRTUAL_FENCE_CROSSING'
  | 'STATIONARY_OBJECT'
  | 'STATIONARY_VEHICLE'
  | 'UNUSUAL_VEHICLE_STOP'
  | 'WRONG_WAY'
  | 'RESTRICTED_ZONE_ACTIVITY'
  | 'NIGHT_MOVEMENT'
  | 'CROWD_DENSITY'
  | 'CROWD_FORMATION'
  | 'ABANDONED_OBJECT'
  | 'REMOVED_OBJECT'
  | 'REPEATED_MOVEMENT'
  | 'RAPID_MOVEMENT'
  | 'SUSPICIOUS_ROUTE'
  | 'WATCHLIST_FACE_MATCH'
  | 'WATCHLIST_PLATE_MATCH';

export interface Rule {
  id: number;
  name: string;
  description?: string;
  event_type: RuleEventType;
  severity: RuleSeverity;
  camera_ids_json: string;
  conditions_json: string;
  schedule_json: string;
  cooldown_seconds: number;
  is_active: boolean;
  created_at: string;
}

export interface AnalyticsStatus {
  engine_name: string;
  total_analyzers: number;
  rule_analyzers_status: string;
  analyzers: Record<string, {
    name: string;
    event_type: string;
    status: string;
    total_evaluations: number;
    total_events_generated: number;
  }>;
  ml_action_model: {
    name: string;
    status: string;
    details: string;
  };
}

export type IncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type IncidentStatus = 'DETECTED' | 'TRIAGED' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED' | 'NEW' | 'FALSE_POSITIVE';

export interface Incident {
  id: number;
  incident_code: string;
  title: string;
  summary: string;
  incident_type: string;
  camera_id: number;
  track_id?: number;
  severity: IncidentSeverity;
  status: IncidentStatus;
  threat_score: number;
  location_name: string;
  correlated_event_ids: string;
  tags_json: string;
  assigned_to?: string;
  assigned_at?: string;
  detected_at: string;
  triaged_at?: string;
  triaged_by?: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  closed_at?: string;
  closed_by?: string;
  resolution_reason?: string;
  resolution_notes?: string;
  transition_history_json?: string;
  operator_notes_json: string;
}

export type EvidenceType = 'CLIP' | 'SNAPSHOT' | 'CROP_PERSON' | 'CROP_VEHICLE' | 'CROP_PLATE' | 'CROP_FACE';

export interface Evidence {
  id: number;
  incident_id?: number;
  camera_id: number;
  file_type: EvidenceType;
  file_path: string;
  file_size_bytes: number;
  sha256_hash: string;
  metadata_json: string;
  created_at: string;
}

export type PlateValidationStatus = 'VALID' | 'INVALID' | 'UNCERTAIN';
export type PlateWatchlistCategory = 'ALLOWLIST' | 'BLOCKLIST' | 'SUSPECT' | 'STOLEN' | 'CUSTOMS_FLAGGED' | 'DIPLOMATIC' | 'WANTED';
export type WatchlistPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ANPRRecord {
  id: number;
  camera_id: number;
  track_id: number;
  raw_text?: string;
  plate_number: string;
  confidence: number;
  validation_status: PlateValidationStatus;
  validation_format: string;
  diagnostics?: string;
  vehicle_type: string;
  vehicle_color?: string;
  vehicle_make?: string;
  vehicle_model?: string;
  is_stationary: boolean;
  dwell_duration_sec: number;
  is_matched: boolean;
  watchlist_category?: string;
  watchlist_priority?: string;
  crop_path?: string;
  vehicle_crop_path?: string;
  full_frame_path?: string;
  evidence_id?: number;
  recording_segment_id?: number;
  timestamp: string;
}

export interface ANPRWatchlist {
  id: number;
  plate_number: string;
  category: PlateWatchlistCategory;
  priority: WatchlistPriority;
  vehicle_model?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VehicleIntelligenceStats {
  total_sightings: number;
  unique_plates: number;
  watchlist_hits: number;
  stationary_vehicles_count: number;
  vehicle_class_distribution: Record<string, number>;
  top_seen_plates: {
    plate_number: string;
    sightings_count: number;
    last_seen?: string;
    vehicle_type: string;
    is_matched: boolean;
  }[];
  recent_flagged_vehicles: ANPRRecord[];
}

export interface ANPRStatus {
  engine_name: string;
  detector_adapter: string;
  detector_status: string;
  ocr_adapter: string;
  ocr_status: string;
  ocr_details: string;
  active_cameras_count: number;
  total_sightings_today: number;
  validation_capabilities: string[];
}

export interface ANPRCaptureResponse {
  success: boolean;
  record_id?: number;
  plate_number?: string;
  raw_text?: string;
  confidence: number;
  ocr_confidence: number;
  validation_status?: string;
  validation_format?: string;
  diagnostics?: string;
  is_matched: boolean;
  watchlist_category?: string;
  watchlist_priority?: string;
  plate_crop_url?: string;
  full_frame_url?: string;
  annotated_frame_url?: string;
  plate_box?: number[];
  error?: string;
}


export type FaceWatchlistCategory = 'WATCH' | 'ALERT' | 'ALLOW' | 'CUSTOM';
export type FaceWatchlistPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type FaceMatchStatus = 'KNOWN' | 'UNKNOWN' | 'UNCERTAIN' | 'UNAVAILABLE';

export interface FaceIdentity {
  id: number;
  name: string;
  identifier?: string;
  unique_person_id?: string;
  notes?: string;
  watchlist_category: FaceWatchlistCategory;
  watchlist_priority: FaceWatchlistPriority;
  is_active: boolean;
  embedding_count: number;
  reference_image_path?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface FaceRecord {
  id: number;
  camera_id: number;
  track_id?: number;
  unique_person_id?: string;
  identity_id?: number;
  identity_name?: string;
  match_status: FaceMatchStatus;
  similarity_score: number;
  recognition_threshold: number;
  watchlist_category?: FaceWatchlistCategory;
  watchlist_priority?: FaceWatchlistPriority;
  bbox_x1?: number;
  bbox_y1?: number;
  bbox_x2?: number;
  bbox_y2?: number;
  quality_score: number;
  sharpness_score: number;
  diagnostics?: string;
  crop_path?: string;
  full_frame_path?: string;
  evidence_id?: number;
  recording_segment_id?: number;
  detector_model?: string;
  embedding_model?: string;
  timestamp: string;
}

export interface FaceStatus {
  engine_name: string;
  detector_adapter: string;
  detector_status: string;
  detector_fps: number;
  detector_latency_ms: number;
  detector_device: string;
  embedding_adapter: string;
  embedding_status: string;
  embedding_dimension: number;
  embedding_latency_ms: number;
  total_identities: number;
  active_watchlist_identities: number;
  total_sightings_today: number;
  hardware_target: string;
}

export interface FaceEnrollmentResponse {
  success: boolean;
  identity_id?: number;
  name?: string;
  quality_score: number;
  sharpness_score: number;
  diagnostics: string;
  embedding_generated: boolean;
  error?: string;
}

export interface SystemHealth {
  cpu_usage_pct: number;
  memory_usage_pct: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_free_gb: number;
  disk_total_gb: number;
  active_cameras: number;
  cameras: {
    camera_id: number;
    name: string;
    status: string;
    fps: number;
    target_fps: number;
    frames_processed: number;
    is_running: boolean;
  }[];
}

export interface AuditLog {
  id: number;
  username: string;
  user_role: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details_json: string;
  ip_address: string;
  timestamp: string;
}

export type AIModelTask =
  | 'DETECTION'
  | 'TRACKING'
  | 'FACE_DETECTION'
  | 'FACE_RECOGNITION'
  | 'ANPR_DETECTION'
  | 'ANPR_OCR'
  | 'POSE_ESTIMATION'
  | 'FALL_DETECTION'
  | 'ACTION_RECOGNITION'
  | 'FIRE_SMOKE_DETECTION'
  | 'WEAPON_DETECTION'
  | 'CROWD_ANALYSIS'
  | 'ATTRIBUTE_ANALYSIS'
  | 'BEHAVIOR'
  | 'NIGHT_ENHANCEMENT';

export type AIModelStatus =
  | 'LOADED'
  | 'ACTIVE'
  | 'STANDBY'
  | 'MODEL_REQUIRED'
  | 'NOT_CONFIGURED'
  | 'UNAVAILABLE'
  | 'ERROR';

export interface AIModel {
  id: number;
  name: string;
  version: string;
  task: AIModelTask;
  provider: string;
  model_path: string;
  format: string;
  input_resolution: string;
  classes_json: string;
  device: string;
  status: AIModelStatus;
  inference_latency_ms: number;
  inference_fps: number;
  memory_mb: number;
  created_at: string;
  updated_at: string;
}

export interface CameraAIProfile {
  id: number;
  camera_id: number;
  person_detection: boolean;
  vehicle_detection: boolean;
  anpr: boolean;
  face_recognition: boolean;
  pose_estimation: boolean;
  fall_detection: boolean;
  fire_smoke: boolean;
  weapon_detection: boolean;
  action_recognition: boolean;
  crowd_analysis: boolean;
  behavior_analytics: boolean;
  attribute_analysis: boolean;
  person_interval_frames: number;
  vehicle_interval_frames: number;
  pose_interval_frames: number;
  fall_interval_frames: number;
  fire_smoke_interval_frames: number;
  weapon_interval_frames: number;
  action_interval_frames: number;
  crowd_interval_frames: number;
  attribute_interval_frames: number;
  detection_threshold: number;
  face_threshold: number;
  anpr_threshold: number;
  pose_threshold: number;
  fall_threshold: number;
  fire_smoke_threshold: number;
  weapon_threshold: number;
  action_threshold: number;
  crowd_density_threshold: number;
  fire_smoke_persistence_sec: number;
  fall_persistence_sec: number;
  weapon_persistence_sec: number;
  crowd_persistence_sec: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PerceptionTelemetry {
  system_cpu_utilization_pct: number;
  process_memory_mb: number;
  ai_models_memory_mb: number;
  active_adapters_count: number;
  total_adapters_count: number;
  adapters: {
    name: string;
    version: string;
    task: string;
    provider: string;
    model_path: string;
    device: string;
    status: string;
    is_loaded: boolean;
    input_resolution: string;
    supported_classes: string[];
    latency_ms: number;
    fps: number;
    total_inferences: number;
    error_count: number;
    last_error?: string;
    last_inference_ts: number;
    memory_mb: number;
  }[];
}

// Phase K: PTZ Control Types
export type PTZConnectionStatus = 'CONNECTED' | 'NOT_CONFIGURED' | 'UNAVAILABLE' | 'UNSUPPORTED' | 'ERROR';

export interface PTZStatus {
  camera_id: number;
  camera_name?: string;
  ptz_enabled: boolean;
  onvif_host: string;
  onvif_port: number;
  status: PTZConnectionStatus;
  pan: number;
  tilt: number;
  zoom: number;
  is_moving: boolean;
  last_action?: string;
  error_message?: string;
}

export interface PTZCapabilities {
  supports_continuous_move: boolean;
  supports_relative_move: boolean;
  supports_absolute_move: boolean;
  supports_zoom: boolean;
  supports_presets: boolean;
  supports_home_position: boolean;
  supports_speed_control: boolean;
  max_presets: number;
  pan_range: number[];
  tilt_range: number[];
  zoom_range: number[];
}

export interface PTZPreset {
  id: number;
  camera_id: number;
  preset_token: string;
  name: string;
  pan: number;
  tilt: number;
  zoom: number;
  is_home: boolean;
  created_at?: string;
}

// Phase K: Tactical Map Types
export interface TacticalCameraFeature {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  altitude_m: number;
  heading_deg: number;
  fov_angle: number;
  range_meters: number;
  status: string;
  location: string;
  group_name: string;
  ptz_enabled: boolean;
  is_night_mode: boolean;
}

export interface TacticalIncidentMarker {
  id: number;
  code: string;
  title: string;
  severity: string;
  status: string;
  threat_score: number;
  camera_id: number;
  location_name: string;
  latitude: number;
  longitude: number;
  detected_at?: string;
}

export interface TacticalMapLayer {
  sector_name: string;
  center_lat: number;
  center_lon: number;
  zoom: number;
  cameras: TacticalCameraFeature[];
  active_incidents: TacticalIncidentMarker[];
  global_tracks: any[];
  topology_links: any[];
  restricted_zones: any[];
  timestamp?: string;
}

// Phase L: Semantic Search & Investigation Case Types
export interface ParsedSemanticQuery {
  raw_query: string;
  object_classes: string[];
  colors: string[];
  attributes: string[];
  locations: string[];
  camera_ids: number[];
  plate_numbers: string[];
  person_names: string[];
  incident_types: string[];
  severities: string[];
  time_range_start?: string;
  time_range_end?: string;
  temporal_expression?: string;
  action_terms: string[];
  explanation: string;
  parser_confidence: number;
}

export interface NLSearchResponse {
  parsed_query: ParsedSemanticQuery;
  total: number;
  limit: number;
  offset: number;
  items: InvestigationSearchResultItem[];
}

export type CaseStatus = 'OPEN' | 'UNDER_INVESTIGATION' | 'RESOLVED' | 'CLOSED';
export type CasePriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface CaseFinding {
  id: number;
  case_id: number;
  item_type: string;
  reference_id?: string;
  camera_id?: number;
  camera_name?: string;
  timestamp?: string;
  title: string;
  notes?: string;
  metadata: Record<string, any>;
  thumbnail_url?: string;
  created_at: string;
}

export interface InvestigationCase {
  id: number;
  case_number: string;
  title: string;
  description?: string;
  status: CaseStatus;
  priority: CasePriority;
  lead_investigator: string;
  hypothesis?: string;
  tags: string[];
  findings_count: number;
  findings: CaseFinding[];
  created_at: string;
  updated_at: string;
  closed_at?: string;
}

export interface InvestigationTimelineEvent {
  id: string;
  timestamp: string;
  camera_id?: number;
  camera_name?: string;
  event_type: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  severity?: string;
  metadata: Record<string, any>;
}

export interface CaseTimelineResponse {
  case_id: number;
  case_number: string;
  title: string;
  total_events: number;
  camera_sequence: {
    camera_id: number;
    camera_name: string;
    first_seen: string;
    last_seen: string;
    sightings_count: number;
  }[];
  events: InvestigationTimelineEvent[];
}

export interface CaseExportResponse {
  case: InvestigationCase;
  timeline: InvestigationTimelineEvent[];
  summary_statistics: {
    total_findings: number;
    cameras_involved: number;
    earliest_event?: string;
    latest_event?: string;
    findings_by_type: Record<string, number>;
  };
  html_report: string;
}

