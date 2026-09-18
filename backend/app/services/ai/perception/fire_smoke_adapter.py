import os
import time
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from app.services.ai.perception.base import BaseModelAdapter, PerceptionTask, ModelStatus, SpecializedDetection

logger = logging.getLogger("arc_vision.perception.fire_smoke")

class FireSmokeDetectorAdapter(BaseModelAdapter):
    """
    Dedicated AI Detector for early flame and thermal smoke detection.
    Includes persistence verification across consecutive frames to prevent false alarms from headlights or glare.
    """
    def __init__(
        self,
        name: str = "Pyros-AI Fire & Smoke Neural Detector",
        version: str = "2.1.0",
        model_path: str = "data/models/fire_smoke_yolov8s.onnx",
        device: str = "CPU",
        persistence_sec: float = 1.5,
        min_confidence: float = 0.45
    ):
        super().__init__(
            name=name,
            version=version,
            task=PerceptionTask.FIRE_SMOKE_DETECTION,
            provider="Custom Trained YOLO / ONNX",
            model_path=model_path,
            device=device,
            input_resolution="640x640",
            supported_classes=["fire", "smoke"]
        )
        self.persistence_sec = persistence_sec
        self.min_confidence = min_confidence
        self._session = None
        
        # State tracking: camera_id -> {"class": str, "first_seen": float, "last_seen": float, "count": int}
        self._detection_history: Dict[str, Dict[str, Any]] = {}

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            self.status = ModelStatus.STANDBY
            self.last_error = f"Fire/Smoke ONNX model weights not present at {self.model_path} (Ready for weights)"
            self.is_loaded = False
            return False

        try:
            import onnxruntime as ort
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "CUDA" in self.device else ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(self.model_path, providers=providers)
            self.status = ModelStatus.ACTIVE
            self.is_loaded = True
            self.memory_mb = 65.0
            logger.info(f"Loaded Fire & Smoke Detector: {self.name} on {self.device}")
            return True
        except Exception as e:
            self.record_error(f"Failed to load fire/smoke model: {str(e)}")
            return False

    def unload(self) -> bool:
        self._session = None
        self.is_loaded = False
        self.status = ModelStatus.STANDBY
        self.memory_mb = 0.0
        return True

    def detect(self, frame: np.ndarray) -> List[SpecializedDetection]:
        if not self.is_loaded or self._session is None:
            return []

        start_t = time.time()
        detections: List[SpecializedDetection] = []
        try:
            # Model inference logic when ONNX model is available
            pass
        except Exception as e:
            self.record_error(str(e))
        finally:
            latency = (time.time() - start_t) * 1000.0
            self.record_inference(latency)
        return detections

    def evaluate_persistence(
        self,
        camera_id: int,
        detections: List[SpecializedDetection],
        current_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Filters raw fire/smoke detections and verifies temporal persistence (> persistence_sec).
        """
        now = current_time or time.time()
        confirmed_events: List[Dict[str, Any]] = []

        for det in detections:
            if det.confidence < self.min_confidence or det.class_name not in ["fire", "smoke"]:
                continue

            key = f"cam_{camera_id}_{det.class_name}"
            if key not in self._detection_history:
                self._detection_history[key] = {
                    "first_seen": now,
                    "last_seen": now,
                    "count": 1,
                    "last_fired": -999.0
                }
            else:
                hist = self._detection_history[key]
                hist["last_seen"] = now
                hist["count"] += 1
                persistence = now - hist["first_seen"]

                if persistence >= self.persistence_sec and (now - hist["last_fired"]) > 20.0:
                    hist["last_fired"] = now
                    event_type = "FIRE_DETECTED" if det.class_name == "fire" else "SMOKE_DETECTED"
                    confirmed_events.append({
                        "event_type": event_type,
                        "class_name": det.class_name,
                        "confidence": det.confidence,
                        "box": det.box,
                        "persistence_sec": round(persistence, 1),
                        "severity": "CRITICAL" if det.class_name == "fire" else "HIGH",
                        "explanation": f"Persistent {det.class_name.upper()} signature detected ({persistence:.1f}s confirmation window, {int(det.confidence * 100)}% confidence)"
                    })

        # Cleanup expired entries (> 5s since last seen)
        stale_keys = [k for k, v in self._detection_history.items() if (now - v["last_seen"]) > 5.0]
        for k in stale_keys:
            del self._detection_history[k]

        return confirmed_events
