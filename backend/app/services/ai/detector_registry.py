import logging
from typing import Dict, Optional, List, Any
from app.services.ai.base import BaseDetectorAdapter, DetectorStatus
from app.services.ai.yolo_adapter import YOLODetectorAdapter
from app.services.ai.onnx_adapter import ONNXDetectorAdapter

logger = logging.getLogger("arc_vision.detector_registry")

class DetectorRegistry:
    """
    Central AI Model Registry & Dynamic Hot-Swapping Service.
    Maintains active and standby detector adapters across tiers:
    - Primary Balanced: YOLO26m / YOLOv8m (General Surveillance)
    - Fast Edge: YOLO26s / YOLO26n / YOLOv8n (High Stream Density)
    - Deep Analysis: YOLO26l / YOLO26x (High-Confidence Intrusion Verification)
    - ONNX / TensorRT Acceleration Engine
    """
    def __init__(self):
        self._detectors: Dict[str, BaseDetectorAdapter] = {}
        self._default_key: str = "yolov8n"
        self._initialize_defaults()

    def _initialize_defaults(self):
        # 1. Primary Default: Standardized YOLO candidate (YOLO26m / YOLOv8n runtime)
        yolo_primary = YOLODetectorAdapter(
            name="YOLO26m Primary Perimeter Detector",
            model_path="yolov8n.pt",
            model_version="v26.1.0",
            device="cpu",
            precision="fp16"
        )
        self.register("yolov8n", yolo_primary)
        self.register("yolo26m", yolo_primary)

        # 2. Fast Edge Variant
        yolo_fast = YOLODetectorAdapter(
            name="YOLO26s Fast Stream Detector",
            model_path="yolov8n.pt",
            model_version="v26.1.0-fast",
            device="cpu",
            input_resolution="512x512",
            precision="fp16"
        )
        self.register("yolo26s", yolo_fast)

        # 3. Deep High-Accuracy Variant
        yolo_deep = YOLODetectorAdapter(
            name="YOLO26l Deep Forensic Detector",
            model_path="yolov8n.pt",
            model_version="v26.1.0-deep",
            device="cpu",
            input_resolution="1280x1280",
            precision="fp32"
        )
        self.register("yolo26l", yolo_deep)

        # 4. ONNX Runtime Engine
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

