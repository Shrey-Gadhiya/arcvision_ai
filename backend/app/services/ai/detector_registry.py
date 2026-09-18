import logging
from typing import Dict, Optional, List, Any
from app.services.ai.base import BaseDetectorAdapter, DetectorStatus
from app.services.ai.yolo_adapter import YOLODetectorAdapter
from app.services.ai.onnx_adapter import ONNXDetectorAdapter

logger = logging.getLogger("arc_vision.detector_registry")

class DetectorRegistry:
    def __init__(self):
        self._detectors: Dict[str, BaseDetectorAdapter] = {}
        self._default_key: str = "yolov8n"
        self._initialize_defaults()

    def _initialize_defaults(self):
        # Register default YOLOv8n detector
        yolo = YOLODetectorAdapter(name="YOLOv8n Perimeter Detector", model_path="yolov8n.pt", device="cpu")
        self.register("yolov8n", yolo)

        # Register ONNX Runtime detector
        onnx_det = ONNXDetectorAdapter(name="ONNX Runtime Detector", model_path="yolov8n.onnx", device="cpu")
        self.register("onnx_yolo", onnx_det)

    def register(self, key: str, adapter: BaseDetectorAdapter):
        self._detectors[key] = adapter
        logger.info(f"Registered detector adapter '{key}': {adapter.name} (Status: {adapter.status.value})")

    def get_detector(self, key: Optional[str] = None) -> BaseDetectorAdapter:
        if key and key in self._detectors:
            return self._detectors[key]
        return self._detectors.get(self._default_key)

    def set_default(self, key: str) -> bool:
        if key in self._detectors:
            self._default_key = key
            logger.info(f"Default system detector switched to: {key}")
            return True
        return False

    def list_detectors(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": k,
                "is_default": k == self._default_key,
                **adapter.get_telemetry()
            }
            for k, adapter in self._detectors.items()
        ]

detector_registry = DetectorRegistry()
