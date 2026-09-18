from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import enum
import numpy as np

class AdapterStatus(str, enum.Enum):
    UNLOADED = "UNLOADED"
    LOADED = "LOADED"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"

class FaceDetectionResult:
    def __init__(
        self,
        box: List[float],  # [x1, y1, x2, y2] relative to full image (0.0 to 1.0) or absolute px
        confidence: float,
        landmarks: Optional[List[List[float]]] = None,
        face_crop: Optional[np.ndarray] = None,
        quality_score: float = 0.0,
        sharpness_score: float = 0.0,
    ):
        self.box = [float(c) for c in box]
        self.confidence = float(confidence)
        self.landmarks = landmarks or []
        self.face_crop = face_crop
        self.quality_score = float(quality_score)
        self.sharpness_score = float(sharpness_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "box": [round(c, 4) for c in self.box],
            "confidence": round(self.confidence, 3),
            "quality_score": round(self.quality_score, 3),
            "sharpness_score": round(self.sharpness_score, 2),
            "landmarks_count": len(self.landmarks)
        }

class FaceEmbeddingResult:
    def __init__(
        self,
        embedding: Optional[List[float]],
        dimension: int = 0,
        normalized: bool = True,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.embedding = [float(x) for x in embedding] if embedding is not None else None
        self.dimension = int(dimension if embedding is None else len(embedding))
        self.normalized = bool(normalized)
        self.status = str(status)
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "normalized": self.normalized,
            "status": self.status,
            "has_embedding": self.embedding is not None and len(self.embedding) > 0
        }

class FaceQualityResult:
    def __init__(
        self,
        passed: bool,
        quality_score: float,
        sharpness_score: float,
        face_count: int,
        diagnostics: str,
        rejected_reason: Optional[str] = None
    ):
        self.passed = bool(passed)
        self.quality_score = float(quality_score)
        self.sharpness_score = float(sharpness_score)
        self.face_count = int(face_count)
        self.diagnostics = str(diagnostics)
        self.rejected_reason = rejected_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "quality_score": round(self.quality_score, 3),
            "sharpness_score": round(self.sharpness_score, 2),
            "face_count": self.face_count,
            "diagnostics": self.diagnostics,
            "rejected_reason": self.rejected_reason
        }

class FaceMatchResult:
    def __init__(
        self,
        status: str,  # "KNOWN", "UNKNOWN", "UNCERTAIN", "UNAVAILABLE"
        identity_id: Optional[int] = None,
        identity_name: Optional[str] = None,
        similarity_score: float = 0.0,
        threshold: float = 0.60,
        watchlist_category: Optional[str] = None,
        watchlist_priority: Optional[str] = None,
        is_matched: bool = False,
        diagnostics: Optional[str] = None
    ):
        self.status = str(status)
        self.identity_id = identity_id
        self.identity_name = identity_name
        self.similarity_score = float(similarity_score)
        self.threshold = float(threshold)
        self.watchlist_category = watchlist_category
        self.watchlist_priority = watchlist_priority
        self.is_matched = bool(is_matched)
        self.diagnostics = diagnostics or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "identity_id": self.identity_id,
            "identity_name": self.identity_name,
            "similarity_score": round(self.similarity_score, 4),
            "threshold": round(self.threshold, 3),
            "watchlist_category": self.watchlist_category,
            "watchlist_priority": self.watchlist_priority,
            "is_matched": self.is_matched,
            "diagnostics": self.diagnostics
        }

class BaseFaceDetectorAdapter(ABC):
    def __init__(self, name: str, device: str = "cpu"):
        self.name = name
        self.device = device
        self.status = AdapterStatus.UNLOADED
        self.last_error: Optional[str] = None
        self.latency_ms: float = 0.0
        self.fps: float = 0.0
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
    def detect_faces(self, image: np.ndarray, confidence_threshold: float = 0.50) -> List[FaceDetectionResult]:
        """Localizes face bounding boxes, landmarks, and confidence."""
        pass

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "device": self.device,
            "latency_ms": round(self.latency_ms, 2),
            "fps": round(self.fps, 1),
            "total_detections": self.total_detections,
            "error": self.last_error
        }

class BaseFaceEmbeddingAdapter(ABC):
    def __init__(self, name: str, device: str = "cpu", dimension: int = 512):
        self.name = name
        self.device = device
        self.dimension = dimension
        self.status = AdapterStatus.UNLOADED
        self.last_error: Optional[str] = None
        self.latency_ms: float = 0.0
        self.total_embeddings: int = 0

    @abstractmethod
    def load(self) -> bool:
        """Initializes face embedding model / weights."""
        pass

    @abstractmethod
    def unload(self) -> bool:
        """Releases embedding model resources."""
        pass

    @abstractmethod
    def compute_embedding(self, face_crop: np.ndarray) -> FaceEmbeddingResult:
        """Extracts normalized L2 embedding vector from a cropped aligned face."""
        pass

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "device": self.device,
            "dimension": self.dimension,
            "latency_ms": round(self.latency_ms, 2),
            "total_embeddings": self.total_embeddings,
            "error": self.last_error
        }
