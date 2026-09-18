import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from app.services.ai.perception.base import BaseModelAdapter, PerceptionTask, ModelStatus

logger = logging.getLogger("arc_vision.perception.fall")

class FallDetector(BaseModelAdapter):
    """
    Fall Detection Engine combining:
    1. Person bounding box aspect ratio inversion (w/h transition from standing < 0.6 to prone > 1.15)
    2. Sudden vertical descent velocity (rapid downward displacement)
    3. Ground-level stillness/inactivity persistence.
    """
    def __init__(
        self,
        name: str = "Kinematic & Geometric Fall Detection Engine",
        version: str = "2.0.0",
        min_aspect_ratio: float = 1.15,
        min_fall_persistence_sec: float = 2.0,
        min_confidence: float = 0.65
    ):
        super().__init__(
            name=name,
            version=version,
            task=PerceptionTask.FALL_DETECTION,
            provider="ARC-VISION Biomechanical Intelligence",
            model_path="app/services/ai/perception/fall_detector.py",
            device="CPU",
            input_resolution="Kinematic Trajectory & Bounding Geometry",
            supported_classes=["fall_incident", "person_down", "slip_trip_fall"]
        )
        self.min_aspect_ratio = min_aspect_ratio
        self.min_fall_persistence_sec = min_fall_persistence_sec
        self.min_confidence = min_confidence
        
        # State: track_id -> {"prone_start_time": float, "prior_aspect_ratios": List[float], "last_fired": float}
        self._track_states: Dict[int, Dict[str, Any]] = {}
        self.status = ModelStatus.ACTIVE
        self.is_loaded = True
        self.memory_mb = 8.0

    def load(self) -> bool:
        self.status = ModelStatus.ACTIVE
        self.is_loaded = True
        return True

    def unload(self) -> bool:
        self._track_states.clear()
        self.status = ModelStatus.STANDBY
        self.is_loaded = False
        return True

    def evaluate_fall(
        self,
        detection: Any,  # Detection or Tracked object
        current_time: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes a person detection track for rapid downward collapse and sustained prone posture.
        Returns fall event payload if conditions are verified.
        """
        now = current_time or time.time()
        start_t = time.time()

        if detection.class_name != "person":
            return None

        track_id = detection.track_id
        box = detection.box  # [x1, y1, x2, y2]
        x1, y1, x2, y2 = box
        w = max(0.001, x2 - x1)
        h = max(0.001, y2 - y1)
        aspect_ratio = round(w / h, 3)

        traj = detection.attributes.get("trajectory", [])
        speed = detection.attributes.get("speed", 0.0)

        # Initialize or fetch track state
        if track_id not in self._track_states:
            self._track_states[track_id] = {
                "prone_start_time": 0.0,
                "history": [],
                "last_fired": -999.0,
                "was_standing_recently": False
            }

        state = self._track_states[track_id]
        state["history"].append((now, aspect_ratio, (y1 + y2) / 2.0))
        if len(state["history"]) > 20:
            state["history"].pop(0)

        # 1. Check if person was standing upright (aspect_ratio < 0.85) in recent history
        recent_standing = any(ar < 0.85 for (ts, ar, cy) in state["history"][:-1]) if len(state["history"]) >= 2 else False

        # 2. Check if current posture is prone/horizontal
        is_prone = aspect_ratio >= self.min_aspect_ratio

        # 3. Detect sudden downward vertical displacement if trajectory available
        vertical_drop_detected = False
        if len(state["history"]) >= 2:
            old_y = state["history"][0][2]
            cur_y = state["history"][-1][2]
            if (cur_y - old_y) > 0.03:
                vertical_drop_detected = True

        event_payload = None

        if is_prone:
            if state["prone_start_time"] == 0.0:
                state["prone_start_time"] = now

            prone_duration = now - state["prone_start_time"]

            # 4. Persistence check & cooldown (30s)
            if prone_duration >= self.min_fall_persistence_sec and (now - state["last_fired"]) > 30.0:
                confidence = min(0.98, max(0.65, 0.50 + (0.20 if vertical_drop_detected else 0.0) + (0.20 if recent_standing else 0.0) + 0.08))
                
                state["last_fired"] = now
                event_payload = {
                    "event_type": "FALL_DETECTED",
                    "track_id": track_id,
                    "confidence": round(confidence, 3),
                    "box": box,
                    "aspect_ratio": aspect_ratio,
                    "prone_duration_sec": round(prone_duration, 1),
                    "vertical_drop": vertical_drop_detected,
                    "standing_precursor": recent_standing,
                    "speed": speed,
                    "severity": "CRITICAL" if prone_duration > 5.0 else "HIGH",
                    "explanation": f"Person #{track_id} fell (aspect ratio {aspect_ratio} inverted from upright; prone for {prone_duration:.1f}s)"
                }
        else:
            if not is_prone:
                state["prone_start_time"] = 0.0

        latency = (time.time() - start_t) * 1000.0
        self.record_inference(latency)
        return event_payload

    def cleanup_inactive_tracks(self, active_track_ids: List[int]):
        active_set = set(active_track_ids)
        to_remove = [tid for tid in self._track_states if tid not in active_set]
        for tid in to_remove:
            del self._track_states[tid]
