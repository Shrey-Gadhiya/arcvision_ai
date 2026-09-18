import abc
import enum
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

class PerceptionTask(str, enum.Enum):
    DETECTION = "DETECTION"
    FACE_DETECTION = "FACE_DETECTION"
    FACE_RECOGNITION = "FACE_RECOGNITION"
    ANPR_DETECTION = "ANPR_DETECTION"
    ANPR_OCR = "ANPR_OCR"
    POSE_ESTIMATION = "POSE_ESTIMATION"
    FALL_DETECTION = "FALL_DETECTION"
    ACTION_RECOGNITION = "ACTION_RECOGNITION"
    FIRE_SMOKE_DETECTION = "FIRE_SMOKE_DETECTION"
    WEAPON_DETECTION = "WEAPON_DETECTION"
    CROWD_ANALYSIS = "CROWD_ANALYSIS"
    ATTRIBUTE_ANALYSIS = "ATTRIBUTE_ANALYSIS"

class ModelStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LOADED = "LOADED"
    STANDBY = "STANDBY"
    MODEL_REQUIRED = "MODEL_REQUIRED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"

class Keypoint2D:
    def __init__(self, name: str, x: float, y: float, score: float):
        self.name = name
        self.x = float(x)  # Normalized 0.0 - 1.0
        self.y = float(y)  # Normalized 0.0 - 1.0
        self.score = float(score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "score": round(self.score, 3)
        }

class PoseDetection:
    def __init__(
        self,
        keypoints: List[Keypoint2D],
        box: List[float],
        confidence: float,
        track_id: int = -1,
        pose_label: Optional[str] = None
    ):
        self.keypoints = keypoints
        self.box = [float(c) for c in box]
        self.confidence = float(confidence)
        self.track_id = int(track_id)
        self.pose_label = pose_label or "standing"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "confidence": round(self.confidence, 3),
            "box": [round(c, 4) for c in self.box],
            "pose_label": self.pose_label,
            "keypoints": [kp.to_dict() for kp in self.keypoints]
        }

class SpecializedDetection:
    def __init__(
        self,
        class_name: str,
        confidence: float,
        box: List[float],
        track_id: int = -1,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.class_name = str(class_name)
        self.confidence = float(confidence)
        self.box = [float(c) for c in box]
        self.track_id = int(track_id)
        self.attributes = attributes or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "box": [round(c, 4) for c in self.box],
            "track_id": self.track_id,
            "attributes": self.attributes
        }

class BaseModelAdapter(abc.ABC):
    """
    Standard interface for all specialized AI perception models.
    Supports honest diagnostics, runtime telemetry, dynamic device selection, and error isolation.
    """
    def __init__(
        self,
        name: str,
        version: str,
        task: PerceptionTask,
        provider: str,
        model_path: str,
        device: str = "CPU",
        input_resolution: str = "640x640",
        supported_classes: Optional[List[str]] = None
    ):
        self.name = name
        self.version = version
        self.task = task
        self.provider = provider
        self.model_path = model_path
        self.device = device.upper()
        self.input_resolution = input_resolution
        self.supported_classes = supported_classes or []
        
        self.status: ModelStatus = ModelStatus.STANDBY
        self.last_error: Optional[str] = None
        self.is_loaded: bool = False
        
        # Runtime Telemetry
        self.latency_ms: float = 0.0
        self.fps: float = 0.0
        self.total_inferences: int = 0
        self.error_count: int = 0
        self.last_inference_ts: float = 0.0
        self.memory_mb: float = 0.0

    @abc.abstractmethod
    def load(self) -> bool:
        """Loads weights and prepares inference engine."""
        pass

    @abc.abstractmethod
    def unload(self) -> bool:
        """Frees model accelerator and memory resources."""
        pass

    def record_inference(self, latency_ms: float):
        self.total_inferences += 1
        self.latency_ms = round(latency_ms, 2)
        self.fps = round(1000.0 / max(0.1, latency_ms), 1)
        self.last_inference_ts = time.time()

    def record_error(self, err_msg: str):
        self.error_count += 1
        self.last_error = str(err_msg)
        self.status = ModelStatus.ERROR

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "task": self.task.value,
            "provider": self.provider,
            "model_path": self.model_path,
            "device": self.device,
            "status": self.status.value,
            "is_loaded": self.is_loaded,
            "input_resolution": self.input_resolution,
            "supported_classes": self.supported_classes,
            "latency_ms": round(self.latency_ms, 2),
            "fps": round(self.fps, 1),
            "total_inferences": self.total_inferences,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_inference_ts": self.last_inference_ts,
            "memory_mb": self.memory_mb
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": self.status in [ModelStatus.ACTIVE, ModelStatus.LOADED, ModelStatus.STANDBY],
            "status": self.status.value,
            "task": self.task.value,
            "device": self.device,
            "error": self.last_error
        }
