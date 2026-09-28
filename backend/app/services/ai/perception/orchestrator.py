import time
import logging
import psutil
from typing import Dict, Any, List, Optional
import numpy as np

from app.services.ai.perception.base import BaseModelAdapter, PerceptionTask, ModelStatus
from app.services.ai.perception.pose_adapter import PoseEstimatorAdapter
from app.services.ai.perception.fall_detector import FallDetector
from app.services.ai.perception.fire_smoke_adapter import FireSmokeDetectorAdapter
from app.services.ai.perception.weapon_adapter import WeaponDetectorAdapter
from app.services.ai.perception.action_adapter import ActionRecognizerAdapter
from app.services.ai.perception.crowd_analyzer import CrowdAnalyzer
from app.services.ai.perception.attribute_adapter import AttributeAnalyzerAdapter
from app.services.ai.perception.open_vocabulary import OpenVocabularyDetectorAdapter
from app.services.ai.perception.segmentation import SAMForensicAdapter
from app.services.ai.perception.depth import DepthEstimationAdapter

logger = logging.getLogger("arc_vision.perception.orchestrator")

class PerceptionOrchestrator:
    """
    Central Multi-Model AI Perception Orchestration Service.
    Coordinates specialized detection models with:
    - Dynamic frame-sampling intervals per task
    - Per-camera AI profile gating
    - Complete exception isolation & fault resilience
    - Unified system-level memory & accelerator telemetry
    """
    def __init__(self):
        # Instantiate modular adapters
        self.pose_adapter = PoseEstimatorAdapter()
        self.fall_detector = FallDetector()
        self.fire_smoke_adapter = FireSmokeDetectorAdapter()
        self.weapon_adapter = WeaponDetectorAdapter()
        self.action_adapter = ActionRecognizerAdapter()
        self.crowd_analyzer = CrowdAnalyzer()
        self.attribute_adapter = AttributeAnalyzerAdapter()
        self.open_vocab_adapter = OpenVocabularyDetectorAdapter()
        self.sam_adapter = SAMForensicAdapter()
        self.depth_adapter = DepthEstimationAdapter()

        self._adapters: Dict[PerceptionTask, BaseModelAdapter] = {
            PerceptionTask.POSE_ESTIMATION: self.pose_adapter,
            PerceptionTask.FALL_DETECTION: self.fall_detector,
            PerceptionTask.FIRE_SMOKE_DETECTION: self.fire_smoke_adapter,
            PerceptionTask.WEAPON_DETECTION: self.weapon_adapter,
            PerceptionTask.ACTION_RECOGNITION: self.action_adapter,
            PerceptionTask.CROWD_ANALYSIS: self.crowd_analyzer,
            PerceptionTask.ATTRIBUTE_ANALYSIS: self.attribute_adapter,
            PerceptionTask.OPEN_VOCABULARY: self.open_vocab_adapter,
            PerceptionTask.SAM_FORENSIC: self.sam_adapter,
            PerceptionTask.DEPTH_ESTIMATION: self.depth_adapter,
        }

        # Initialize lightweight/deterministic analyzers
        self.fall_detector.load()
        self.crowd_analyzer.load()
        # Attempt loading neural models if weights exist on disk
        self.pose_adapter.load()
        self.fire_smoke_adapter.load()
        self.weapon_adapter.load()
        self.action_adapter.load()
        self.attribute_adapter.load()
        self.open_vocab_adapter.load()
        self.sam_adapter.load()
        self.depth_adapter.load()

    def get_adapter(self, task: PerceptionTask) -> Optional[BaseModelAdapter]:
        return self._adapters.get(task)

    def process_camera_frame(
        self,
        camera_id: int,
        frame: np.ndarray,
        frame_idx: int,
        tracked_objects: List[Any],
        zones: List[Dict[str, Any]],
        ai_profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes active specialized perception tasks for a frame based on configured sampling intervals.
        Guarantees fault isolation: any unhandled exception in a model is captured without breaking the stream.
        """
        events: List[Dict[str, Any]] = []
        profile = ai_profile or {}

        # 1. Fall Detection Evaluation (every N frames, default 3)
        fall_enabled = profile.get("fall_detection", True)
        fall_interval = profile.get("fall_interval_frames", 3)
        if fall_enabled and (frame_idx % fall_interval == 0):
            try:
                for obj in tracked_objects:
                    if obj.class_name == "person":
                        fall_evt = self.fall_detector.evaluate_fall(obj)
                        if fall_evt:
                            fall_evt["camera_id"] = camera_id
                            events.append(fall_evt)
            except Exception as e:
                logger.error(f"[Fault-Isolation] FallDetector error on Cam #{camera_id}: {e}")
                self.fall_detector.record_error(str(e))

        # 2. Crowd Density Analytics (every N frames, default 6)
        crowd_enabled = profile.get("crowd_analysis", True)
        crowd_interval = profile.get("crowd_interval_frames", 6)
        if crowd_enabled and (frame_idx % crowd_interval == 0) and zones:
            try:
                crowd_thresh = profile.get("crowd_density_threshold", 8)
                crowd_evts = self.crowd_analyzer.analyze_crowd(
                    camera_id=camera_id,
                    tracked_persons=tracked_objects,
                    zones=zones,
                    threshold=crowd_thresh
                )
                events.extend(crowd_evts)
            except Exception as e:
                logger.error(f"[Fault-Isolation] CrowdAnalyzer error on Cam #{camera_id}: {e}")
                self.crowd_analyzer.record_error(str(e))

        # 3. Fire & Smoke Neural Detection (every N frames, default 6)
        fire_enabled = profile.get("fire_smoke", True)
        fire_interval = profile.get("fire_smoke_interval_frames", 6)
        if fire_enabled and (frame_idx % fire_interval == 0) and self.fire_smoke_adapter.is_loaded:
            try:
                raw_fire_dets = self.fire_smoke_adapter.detect(frame)
                if raw_fire_dets:
                    fire_evts = self.fire_smoke_adapter.evaluate_persistence(camera_id, raw_fire_dets)
                    for fe in fire_evts:
                        fe["camera_id"] = camera_id
                        events.append(fe)
            except Exception as e:
                logger.error(f"[Fault-Isolation] FireSmokeDetector error on Cam #{camera_id}: {e}")
                self.fire_smoke_adapter.record_error(str(e))

        # 4. Dangerous Object / Weapon Detection (every N frames, default 4)
        weapon_enabled = profile.get("weapon_detection", True)
        weapon_interval = profile.get("weapon_interval_frames", 4)
        if weapon_enabled and (frame_idx % weapon_interval == 0):
            try:
                # Check for weapons or weapon classes in tracked objects
                for obj in tracked_objects:
                    cname = getattr(obj, "class_name", "").lower()
                    if cname in ["knife", "gun", "pistol", "rifle", "weapon", "scissors"]:
                        events.append({
                            "event_type": "DANGEROUS_OBJECT_DETECTED",
                            "severity": "CRITICAL",
                            "camera_id": camera_id,
                            "track_id": obj.track_id,
                            "class_name": cname.upper(),
                            "box": obj.box,
                            "confidence": obj.confidence,
                            "explanation": f"High-threat weapon / bladed object detected ({cname.upper()}, {int(obj.confidence * 100)}% confidence)"
                        })
                        obj.attributes["is_weapon"] = True

                if self.weapon_adapter.is_loaded:
                    raw_weapon_dets = self.weapon_adapter.detect(frame)
                    for wd in raw_weapon_dets:
                        wevt = self.weapon_adapter.build_weapon_event(wd, camera_id)
                        wevt["camera_id"] = camera_id
                        events.append(wevt)
            except Exception as e:
                logger.error(f"[Fault-Isolation] WeaponDetector error on Cam #{camera_id}: {e}")
                self.weapon_adapter.record_error(str(e))

        # 5. Drone & Aerial Threat Detection (every N frames, default 3)
        drone_enabled = profile.get("drone_detection", True)
        drone_interval = profile.get("drone_interval_frames", 3)
        if drone_enabled and (frame_idx % drone_interval == 0):
            try:
                from app.services.ai.perception.drone_adapter import drone_detector
                d_evts = drone_detector.detect_aerial_objects(frame, tracked_objects, camera_id)
                events.extend(d_evts)
            except Exception as e:
                logger.error(f"[Fault-Isolation] DroneDetector error on Cam #{camera_id}: {e}")

        # 6. Face Concealment & Masking Detection (every N frames, default 4)
        face_concealment_enabled = profile.get("face_concealment", True)
        concealment_interval = profile.get("concealment_interval_frames", 4)
        if face_concealment_enabled and (frame_idx % concealment_interval == 0):
            try:
                from app.services.ai.face.face_concealment_detector import face_concealment_detector
                for obj in tracked_objects:
                    if getattr(obj, "class_name", "") in ["person", "human", "pedestrian"]:
                        c_evt = face_concealment_detector.analyze_person_face_visibility(
                            frame=frame,
                            person_box=obj.box,
                            track_id=obj.track_id,
                            camera_id=camera_id
                        )
                        if c_evt:
                            events.append(c_evt)
                            obj.attributes["face_concealed"] = True
                            obj.attributes["concealment_type"] = c_evt.get("concealment_type")
            except Exception as e:
                logger.error(f"[Fault-Isolation] FaceConcealment error on Cam #{camera_id}: {e}")

        # 7. Unattended & Suspicious Package Detection (every N frames, default 5)
        unattended_enabled = profile.get("unattended_objects", True)
        unattended_interval = profile.get("unattended_interval_frames", 5)
        if unattended_enabled and (frame_idx % unattended_interval == 0):
            try:
                from app.services.ai.perception.unattended_object_adapter import unattended_object_detector
                u_evts = unattended_object_detector.evaluate_unattended_objects(camera_id, tracked_objects)
                events.extend(u_evts)
            except Exception as e:
                logger.error(f"[Fault-Isolation] UnattendedObjectDetector error on Cam #{camera_id}: {e}")

        # 8. Pose Estimation (every N frames, default 3)
        pose_enabled = profile.get("pose_estimation", False)
        pose_interval = profile.get("pose_interval_frames", 3)
        if pose_enabled and (frame_idx % pose_interval == 0):
            try:
                for obj in tracked_objects:
                    if obj.class_name == "person":
                        if self.pose_adapter.is_loaded:
                            pass
                        else:
                            pose_det = self.pose_adapter.extract_pose_from_geometry(obj.box, obj.track_id)
                            obj.attributes["pose"] = pose_det.to_dict()
            except Exception as e:
                logger.error(f"[Fault-Isolation] PoseEstimator error on Cam #{camera_id}: {e}")
                self.pose_adapter.record_error(str(e))

        return events

    def get_system_telemetry(self) -> Dict[str, Any]:
        """
        Gathers aggregated hardware, memory, and adapter telemetry across the platform.
        """
        process = psutil.Process()
        mem_info = process.memory_info()
        cpu_percent = psutil.cpu_percent(interval=None)

        adapters_telemetry = [adapter.get_telemetry() for adapter in self._adapters.values()]
        total_model_memory = sum(adapter.memory_mb for adapter in self._adapters.values())

        return {
            "system_cpu_utilization_pct": cpu_percent,
            "process_memory_mb": round(mem_info.rss / (1024 * 1024), 2),
            "ai_models_memory_mb": round(total_model_memory, 2),
            "active_adapters_count": sum(1 for a in self._adapters.values() if a.status == ModelStatus.ACTIVE),
            "total_adapters_count": len(self._adapters),
            "adapters": adapters_telemetry
        }

# Global Singleton Instance
perception_orchestrator = PerceptionOrchestrator()
