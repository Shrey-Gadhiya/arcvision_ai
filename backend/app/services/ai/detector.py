from app.services.ai.base import BaseDetectorAdapter, Detection, DetectorStatus
from app.services.ai.yolo_adapter import YOLODetectorAdapter, SURVEILLANCE_CLASSES
from app.services.ai.onnx_adapter import ONNXDetectorAdapter
from app.services.ai.detector_registry import detector_registry

# Backward compatible proxy for detector_service
class DetectorServiceProxy(BaseDetectorAdapter):
    def __init__(self):
        self._registry = detector_registry

    @property
    def active_detector(self) -> BaseDetectorAdapter:
        return self._registry.get_detector()

    def load(self) -> bool:
        return self.active_detector.load()

    def unload(self) -> bool:
        return self.active_detector.unload()

    def detect(self, frame, confidence_threshold: float = 0.35):
        return self.active_detector.detect(frame, confidence_threshold=confidence_threshold)

    def get_supported_classes(self):
        return self.active_detector.get_supported_classes()

    def get_telemetry(self):
        return self.active_detector.get_telemetry()

    def health_check(self):
        return self.active_detector.health_check()

detector_service = DetectorServiceProxy()
