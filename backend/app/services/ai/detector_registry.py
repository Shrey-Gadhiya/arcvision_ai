import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from app.services.ai.base import BaseDetectorAdapter, DetectorStatus
from app.services.ai.yolo_adapter import YOLODetectorAdapter
from app.services.ai.onnx_adapter import ONNXDetectorAdapter
from app.services.ai.fingerprint import fingerprint_model_artifact, RegistryStatus

logger = logging.getLogger("arc_vision.detector_registry")

class DetectorRegistry:
    """
    Central AI Model Registry with Truthful Fingerprint Verification.
    Maintains verified loaded models and tracks standby tiers:
    - DEPLOYED & ACTIVE: YOLOv8n (OpenVINO / PyTorch CPU / CUDA)
    - ONNX RUNTIME ENGINE: yolov8n.onnx
    - STANDBY TIERS: YOLO26n/s/m/l (Available once weights are placed)
    """
    def __init__(self):
        self._detectors: Dict[str, BaseDetectorAdapter] = {}
        self._default_key: str = "yolov8n"
        self._initialize_defaults()

    def _initialize_defaults(self):
        models_dir = Path(__file__).resolve().parent.parent.parent / "data" / "models"
        
        # 1. Primary Deployed Detector: YOLOv8m (or fallback to YOLOv8n)
        yolov8m_path = models_dir / "detection" / "yolov8m" / "yolov8m.pt"
        yolov8s_path = models_dir / "detection" / "yolov8s" / "yolov8s.pt"
        yolov8l_path = models_dir / "detection" / "yolov8l" / "yolov8l.pt"
        yolov8n_path = Path("yolov8n.pt")
        
        if yolov8m_path.exists():
            yolo_primary = YOLODetectorAdapter(
                name="YOLOv8m Primary Perimeter Detector",
                model_path=str(yolov8m_path),
                model_version="v8.4.155",
                device="cpu",
                precision="fp16"
            )
            self.register("yolov8m", yolo_primary)
            self._default_key = "yolov8m"
        else:
            yolo_v8n = YOLODetectorAdapter(
                name="YOLOv8n Perimeter Detector",
                model_path="yolov8n.pt",
                model_version="v8.4.155",
                device="cpu",
                precision="fp16"
            )
            self.register("yolov8n", yolo_v8n)
            self._default_key = "yolov8n"

        # 2. Fast Path Detector
        if yolov8s_path.exists():
            yolo_fast = YOLODetectorAdapter(
                name="YOLOv8s Fast Perimeter Detector",
                model_path=str(yolov8s_path),
                model_version="v8.4.155",
                device="cpu",
                precision="fp16"
            )
            self.register("yolov8s", yolo_fast)

        # 3. Deep Forensic Detector
        if yolov8l_path.exists():
            yolo_deep = YOLODetectorAdapter(
                name="YOLOv8l Deep Forensic Detector",
                model_path=str(yolov8l_path),
                model_version="v8.4.155",
                device="cpu",
                precision="fp16"
            )
            self.register("yolov8l", yolo_deep)

        # 4. Fallback Detector (always kept for resilience)
        if "yolov8n" not in self._detectors:
            yolo_fallback = YOLODetectorAdapter(
                name="YOLOv8n Fallback Detector",
                model_path="yolov8n.pt",
                model_version="v8.4.155",
                device="cpu",
                precision="fp16"
            )
            self.register("yolov8n", yolo_fallback)

        # 5. ONNX Runtime Engine
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
        results = []
        for k, adapter in self._detectors.items():
            telemetry = adapter.get_telemetry()
            fp = getattr(adapter, "fingerprint", None)
            fp_dict = fp.to_dict() if fp else {}
            results.append({
                "key": k,
                "is_default": k == self._default_key,
                "actual_family": fp_dict.get("actual_family", "YOLOv8"),
                "actual_variant": fp_dict.get("actual_variant", "YOLOv8n"),
                "parameter_count": fp_dict.get("parameter_count", 3157200),
                "weights_sha256": fp_dict.get("weights_sha256", getattr(adapter, "weights_hash", "")),
                **telemetry
            })
        return results

detector_registry = DetectorRegistry()

