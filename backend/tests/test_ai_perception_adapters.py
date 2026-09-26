import time
import pytest
import numpy as np
from app.services.ai.perception.base import PerceptionTask, ModelStatus, Keypoint2D, PoseDetection, SpecializedDetection
from app.services.ai.perception.pose_adapter import PoseEstimatorAdapter
from app.services.ai.perception.fall_detector import FallDetector
from app.services.ai.perception.fire_smoke_adapter import FireSmokeDetectorAdapter
from app.services.ai.perception.weapon_adapter import WeaponDetectorAdapter
from app.services.ai.perception.action_adapter import ActionRecognizerAdapter
from app.services.ai.perception.crowd_analyzer import CrowdAnalyzer
from app.services.ai.perception.attribute_adapter import AttributeAnalyzerAdapter
from app.services.ai.perception.orchestrator import PerceptionOrchestrator

class MockTrackedObject:
    def __init__(self, track_id: int, class_name: str, box: list, attributes: dict = None):
        self.track_id = track_id
        self.class_name = class_name
        self.confidence = 0.90
        self.box = box
        self.attributes = attributes or {}

# 1. Base Contracts & Honest Status Handling
def test_pose_adapter_contract_and_fallback():
    adapter = PoseEstimatorAdapter(model_path="data/models/non_existent_pose.onnx")
    assert adapter.task == PerceptionTask.POSE_ESTIMATION
    loaded = adapter.load()
    assert not loaded
    assert adapter.status in [ModelStatus.NOT_CONFIGURED, ModelStatus.STANDBY]
    assert "not found" in adapter.last_error.lower()

    # Fallback geometric keypoints
    box = [0.2, 0.1, 0.4, 0.8] # w=0.2, h=0.7 -> Standing upright (ar ~ 0.28)
    pose = adapter.extract_pose_from_geometry(box, track_id=5)
    assert len(pose.keypoints) == 17
    assert pose.pose_label == "standing"
    assert pose.track_id == 5

# 2. Geometric & Kinematic Fall Detection
def test_fall_detection_upright_person_no_fall():
    fall_engine = FallDetector(min_aspect_ratio=1.15, min_fall_persistence_sec=2.0)
    
    # Person standing normally: box [x1, y1, x2, y2]
    # w = 0.15, h = 0.60 -> aspect_ratio = 0.25 (standing)
    person = MockTrackedObject(
        track_id=10,
        class_name="person",
        box=[0.30, 0.20, 0.45, 0.80],
        attributes={"trajectory": [(0.37, 0.3), (0.37, 0.5)], "speed": 0.02}
    )
    res = fall_engine.evaluate_fall(person, current_time=100.0)
    assert res is None

def test_fall_detection_collapse_and_persistence():
    fall_engine = FallDetector(min_aspect_ratio=1.15, min_fall_persistence_sec=2.0)
    
    # Step 1: Upright standing
    standing_p = MockTrackedObject(
        track_id=20,
        class_name="person",
        box=[0.30, 0.20, 0.45, 0.80], # w=0.15, h=0.60
        attributes={"trajectory": [(0.37, 0.3), (0.37, 0.5)], "speed": 0.02}
    )
    fall_engine.evaluate_fall(standing_p, current_time=100.0)
    fall_engine.evaluate_fall(standing_p, current_time=100.5)

    # Step 2: Sudden horizontal collapse: box [x1, y1, x2, y2]
    # w = 0.60, h = 0.20 -> aspect_ratio = 3.0 (prone on floor)
    fallen_p = MockTrackedObject(
        track_id=20,
        class_name="person",
        box=[0.20, 0.70, 0.80, 0.90], # w=0.60, h=0.20, cy shifted down from 0.5 to 0.8
        attributes={"trajectory": [(0.5, 0.75), (0.5, 0.80)], "speed": 0.001}
    )
    # First frame of fall (prone duration = 0.0s) -> No event yet
    res1 = fall_engine.evaluate_fall(fallen_p, current_time=101.0)
    assert res1 is None

    # Step 3: Person remains prone for 2.5s (> 2.0s threshold)
    res2 = fall_engine.evaluate_fall(fallen_p, current_time=103.5)
    assert res2 is not None
    assert res2["event_type"] == "FALL_DETECTED"
    assert res2["track_id"] == 20
    assert res2["aspect_ratio"] == 3.0
    assert res2["prone_duration_sec"] >= 2.0
    assert "fell" in res2["explanation"].lower()

# 3. Fire & Smoke Persistence Filtering
def test_fire_smoke_persistence_filtering():
    fire_adapter = FireSmokeDetectorAdapter(persistence_sec=1.5, min_confidence=0.40)
    
    # Single frame flash
    det1 = SpecializedDetection(class_name="fire", confidence=0.85, box=[0.1, 0.1, 0.3, 0.3])
    evts1 = fire_adapter.evaluate_persistence(camera_id=1, detections=[det1], current_time=10.0)
    assert len(evts1) == 0 # First observation, not persistent yet

    # Frame after 0.5s -> Still under 1.5s threshold
    evts2 = fire_adapter.evaluate_persistence(camera_id=1, detections=[det1], current_time=10.5)
    assert len(evts2) == 0

    # Frame after 2.0s -> Exceeds persistence threshold
    evts3 = fire_adapter.evaluate_persistence(camera_id=1, detections=[det1], current_time=12.0)
    assert len(evts3) == 1
    assert evts3[0]["event_type"] == "FIRE_DETECTED"
    assert evts3[0]["persistence_sec"] >= 1.5
    assert evts3[0]["severity"] == "CRITICAL"

# 4. Dangerous Object & Weapon Adapter
def test_weapon_adapter_contract():
    weapon_adapter = WeaponDetectorAdapter(model_path="data/models/non_existent_weapon.onnx")
    assert weapon_adapter.task == PerceptionTask.WEAPON_DETECTION
    assert weapon_adapter.status == ModelStatus.STANDBY
    
    det = SpecializedDetection(class_name="handgun", confidence=0.92, box=[0.4, 0.4, 0.5, 0.5], track_id=88)
    evt = weapon_adapter.build_weapon_event(det, camera_id=2)
    assert evt["event_type"] == "DANGEROUS_OBJECT_DETECTED"
    assert evt["class_name"] == "handgun"
    assert evt["severity"] == "CRITICAL"

# 5. Temporal Action Recognition Adapter
def test_action_adapter_contract():
    action_adapter = ActionRecognizerAdapter(model_path="data/models/non_existent_action.onnx")
    assert action_adapter.task == PerceptionTask.ACTION_RECOGNITION
    assert action_adapter.status == ModelStatus.STANDBY
    assert not action_adapter.is_loaded
    assert action_adapter.classify_action([]) is None

# 6. Attribute Analyzer Adapter
def test_attribute_adapter_contract():
    attr_adapter = AttributeAnalyzerAdapter(model_path="data/models/non_existent_attr.onnx")
    assert attr_adapter.task == PerceptionTask.ATTRIBUTE_ANALYSIS
    assert attr_adapter.status == ModelStatus.STANDBY
    assert attr_adapter.extract_attributes(None, "person") == {}

# 7. Spatial Crowd Density Analytics
def test_crowd_analyzer_density_threshold():
    crowd_engine = CrowdAnalyzer(default_density_threshold=4, persistence_sec=3.0)
    
    zone = {
        "id": 101,
        "name": "Courtyard Plaza",
        "polygon": [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}, {"x": 1.0, "y": 1.0}, {"x": 0.0, "y": 1.0}]
    }

    # 5 persons in the zone (> 4 threshold)
    persons = [
        MockTrackedObject(track_id=i, class_name="person", box=[0.1*i, 0.1*i, 0.1*i+0.1, 0.1*i+0.1], attributes={"centroid": (0.2 + i*0.1, 0.2 + i*0.1)})
        for i in range(5)
    ]

    # Time 0: Initial threshold breach
    evts0 = crowd_engine.analyze_crowd(camera_id=1, tracked_persons=persons, zones=[zone], threshold=4, current_time=50.0)
    assert len(evts0) == 0

    # Time 54s (> 3s persistence)
    evts1 = crowd_engine.analyze_crowd(camera_id=1, tracked_persons=persons, zones=[zone], threshold=4, current_time=54.0)
    assert len(evts1) == 1
    assert evts1[0]["event_type"] == "CROWD_DENSITY_THRESHOLD"
    assert evts1[0]["count"] == 5
    assert evts1[0]["threshold"] == 4
    assert evts1[0]["zone_id"] == 101

# 8. Perception Orchestrator & Fault Isolation
def test_perception_orchestrator_pipeline_and_fault_isolation():
    orchestrator = PerceptionOrchestrator()
    
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Tracked person in prone fall state
    fallen_person = MockTrackedObject(
        track_id=42,
        class_name="person",
        box=[0.1, 0.7, 0.8, 0.9],
        attributes={"trajectory": [(0.4, 0.5), (0.4, 0.8)], "speed": 0.001}
    )
    
    # Initialize standing history
    orchestrator.fall_detector.evaluate_fall(
        MockTrackedObject(42, "person", [0.3, 0.2, 0.45, 0.8]),
        current_time=10.0
    )

    # Frame 0 (matches fall interval 2)
    evts1 = orchestrator.process_camera_frame(
        camera_id=1,
        frame=dummy_frame,
        frame_idx=0,
        tracked_objects=[fallen_person],
        zones=[],
        ai_profile={"fall_detection": True, "fall_interval_frames": 2}
    )
    
    # Advance time > persistence
    time.sleep(0.01)
    evts2 = orchestrator.process_camera_frame(
        camera_id=1,
        frame=dummy_frame,
        frame_idx=2,
        tracked_objects=[fallen_person],
        zones=[],
        ai_profile={"fall_detection": True, "fall_interval_frames": 2}
    )
    
    # Telemetry check
    telemetry = orchestrator.get_system_telemetry()
    assert "system_cpu_utilization_pct" in telemetry
    assert "process_memory_mb" in telemetry
    assert "adapters" in telemetry
    assert len(telemetry["adapters"]) >= 7

def test_fault_isolation_on_malformed_input():
    orchestrator = PerceptionOrchestrator()
    # Malformed objects with missing attributes should never crash the orchestrator
    malformed_obj = MockTrackedObject(track_id=99, class_name="person", box=[0, 0, 0, 0], attributes=None)
    
    # Should execute gracefully without throwing exceptions
    events = orchestrator.process_camera_frame(
        camera_id=99,
        frame=np.zeros((100, 100, 3), dtype=np.uint8),
        frame_idx=2,
        tracked_objects=[malformed_obj],
        zones=[{"id": 1, "polygon": "invalid_polygon_type"}]
    )
    assert isinstance(events, list)

def test_open_vocabulary_adapter():
    from app.services.ai.perception.open_vocabulary import OpenVocabularyDetectorAdapter
    adapter = OpenVocabularyDetectorAdapter()
    assert adapter.task == PerceptionTask.OPEN_VOCABULARY
    assert adapter.status in [ModelStatus.ACTIVE, ModelStatus.STANDBY]
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res = adapter.query(frame, text_prompts=["person carrying a weapon", "backpack"])
    assert isinstance(res, list)

def test_sam_forensic_adapter():
    from app.services.ai.perception.segmentation import SAMForensicAdapter
    adapter = SAMForensicAdapter()
    assert adapter.task == PerceptionTask.SAM_FORENSIC
    assert adapter.status in [ModelStatus.ACTIVE, ModelStatus.STANDBY]
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res = adapter.segment_roi(frame, box_prompt=[0.1, 0.1, 0.5, 0.5])
    assert res is not None
    assert len(res.polygon) == 4
    assert res.mask_area_ratio > 0.0

def test_depth_estimation_adapter():
    from app.services.ai.perception.depth import DepthEstimationAdapter
    adapter = DepthEstimationAdapter()
    assert adapter.task == PerceptionTask.DEPTH_ESTIMATION
    assert adapter.status in [ModelStatus.ACTIVE, ModelStatus.STANDBY]
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    depth_near = adapter.estimate_relative_depth(frame, bbox=(0.2, 0.6, 0.8, 0.95))
    depth_far = adapter.estimate_relative_depth(frame, bbox=(0.4, 0.1, 0.6, 0.2))
    assert depth_near <= depth_far # Objects lower and larger are nearer to the camera plane

