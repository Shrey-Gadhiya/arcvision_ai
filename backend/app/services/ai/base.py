from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import enum
import time
import numpy as np

class DetectorStatus(str, enum.Enum):
    UNLOADED = "UNLOADED"
    LOADED = "LOADED"
    ERROR = "ERROR"
    NOT_SUPPORTED = "NOT_SUPPORTED"

class Detection:
    def __init__(
        self,
        class_name: str,
        confidence: float,
        box: List[float],  # [x1, y1, x2, y2] normalized (0.0 to 1.0)
        track_id: int = -1,
        attributes: Dict[str, Any] = None
    ):
        self.class_name = str(class_name)
        self.confidence = float(confidence)
        self.box = [float(c) for c in box]
        self.track_id = int(track_id)
        self.attributes = attributes or {}

    def copy(self) -> 'Detection':
        return Detection(
            class_name=self.class_name,
            confidence=self.confidence,
            box=list(self.box),
            track_id=self.track_id,
            attributes=dict(self.attributes)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "confidence": round(float(self.confidence), 3),
            "box": [round(float(coord), 4) for coord in self.box],
            "track_id": self.track_id,
            "attributes": self.attributes
        }

class BaseDetectorAdapter(ABC):
    def __init__(
        self,
        name: str,
        model_path: str,
        device: str = "cpu",
        input_resolution: str = "640x640"
    ):
        self.name = name
        self.model_path = model_path
        self.device = device
        self.input_resolution = input_resolution
        self.status = DetectorStatus.UNLOADED
        self.last_error: Optional[str] = None
        
        # Telemetry
        self.inference_latency_ms: float = 0.0
        self.inference_fps: float = 0.0
        self.total_inferences: int = 0
        self.error_count: int = 0
        self.last_inference_ts: float = 0.0

    @abstractmethod
    def load(self) -> bool:
        """Loads model weights and initializes execution provider."""
        pass

    @abstractmethod
    def unload(self) -> bool:
        """Releases model memory and accelerator context."""
        pass

    @abstractmethod
    def detect(self, frame: np.ndarray, confidence_threshold: float = 0.35) -> List[Detection]:
        """Runs synchronous inference and returns domain detections."""
        pass

    @abstractmethod
    def get_supported_classes(self) -> List[str]:
        """Returns the list of target classes detectable by this adapter."""
        pass

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model_path": self.model_path,
            "device": self.device,
            "status": self.status.value,
            "input_resolution": self.input_resolution,
            "inference_latency_ms": round(self.inference_latency_ms, 2),
            "inference_fps": round(self.inference_fps, 2),
            "total_inferences": self.total_inferences,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_inference_ts": self.last_inference_ts
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": self.status == DetectorStatus.LOADED,
            "status": self.status.value,
            "error": self.last_error,
            "device": self.device
        }
