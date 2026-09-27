from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import enum
import time
import numpy as np

class AdapterStatus(str, enum.Enum):
    UNLOADED = "UNLOADED"
    LOADED = "LOADED"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"

class PlateDetectionResult:
    def __init__(
        self,
        box: List[float],  # [x1, y1, x2, y2] relative to vehicle crop (0.0 to 1.0)
        confidence: float,
        plate_crop: Optional[np.ndarray] = None
    ):
        self.box = [float(c) for c in box]
        self.confidence = float(confidence)
        self.plate_crop = plate_crop

    def to_dict(self) -> Dict[str, Any]:
        return {
            "box": [round(c, 4) for c in self.box],
            "confidence": round(self.confidence, 3)
        }

class OCRResult:
    def __init__(
        self,
        raw_text: str,
        confidence: float,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.raw_text = str(raw_text or "")
        self.confidence = float(confidence)
        self.status = status
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "confidence": round(self.confidence, 3),
            "status": self.status,
            "metadata": self.metadata
        }

class ValidationOutcome:
    def __init__(
        self,
        status: str,  # "VALID", "INVALID", "UNCERTAIN"
        format_name: str,  # "INDIAN_STANDARD", "BHARAT_SERIES", "DEFENCE_BORDER", "REGIONAL", "UNKNOWN"
        confidence: float,
        diagnostics: Optional[str] = None
    ):
        self.status = status
        self.format_name = format_name
        self.confidence = float(confidence)
        self.diagnostics = diagnostics or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "format_name": self.format_name,
            "confidence": round(self.confidence, 3),
            "diagnostics": self.diagnostics
        }

class BasePlateDetectorAdapter(ABC):
    def __init__(self, name: str, device: str = "cpu"):
        self.name = name
        self.device = device
        self.status = AdapterStatus.UNLOADED
        self.last_error: Optional[str] = None
        self.latency_ms: float = 0.0
        self.total_detections: int = 0

    @abstractmethod
    def load(self) -> bool:
        """Loads model weights/engine."""
        pass

    @abstractmethod
    def unload(self) -> bool:
        """Unloads weights and frees memory."""
        pass

    @abstractmethod
    def detect_plates(self, vehicle_crop: np.ndarray, confidence_threshold: float = 0.40) -> List[PlateDetectionResult]:
        """Localizes plate bounding boxes within a cropped vehicle image."""
        pass

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "device": self.device,
            "latency_ms": round(self.latency_ms, 2),
            "total_detections": self.total_detections,
            "error": self.last_error
        }

class BasePlateOCRAdapter(ABC):
    def __init__(self, name: str, device: str = "cpu"):
        self.name = name
        self.device = device
        self.status = AdapterStatus.UNLOADED
        self.last_error: Optional[str] = None
        self.latency_ms: float = 0.0
        self.total_reads: int = 0

    @abstractmethod
    def load(self) -> bool:
        """Initializes OCR engine / weights."""
        pass

    @abstractmethod
    def unload(self) -> bool:
        """Releases OCR engine resources."""
        pass

    @abstractmethod
    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        """Extracts text and confidence from a cropped license plate image."""
        pass

    def detect_and_read_from_frame(self, frame_or_crop: np.ndarray) -> Optional[Dict[str, Any]]:
        """Extracts plate text and bounding geometry from a vehicle frame/crop."""
        if frame_or_crop is None or frame_or_crop.size == 0:
            return None
        res = self.read_plate(frame_or_crop)
        if res.raw_text and len(res.raw_text) >= 3 and res.confidence >= 0.20:
            h, w = frame_or_crop.shape[:2]
            return {
                "raw_text": res.metadata.get("raw", res.raw_text),
                "cleaned_text": res.raw_text,
                "confidence": res.confidence,
                "box": [0, 0, w, h],
                "plate_crop": frame_or_crop,
                "box_rel": [0.0, 0.0, 1.0, 1.0]
            }
        return None

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "device": self.device,
            "latency_ms": round(self.latency_ms, 2),
            "total_reads": self.total_reads,
            "error": self.last_error
        }
