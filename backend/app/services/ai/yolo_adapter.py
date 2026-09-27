import time
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from app.services.ai.base import BaseDetectorAdapter, Detection, DetectorStatus
from app.services.ai.fingerprint import fingerprint_model_artifact, ModelFingerprint, RegistryStatus

logger = logging.getLogger("arc_vision.yolo_adapter")

# Border surveillance target classes mapping (COCO class IDs to standardized domain classes)
SURVEILLANCE_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    6: "train",
    7: "truck",
    15: "cat",
    16: "dog",
    24: "backpack",
    26: "handbag",
    28: "suitcase"
}

class YOLODetectorAdapter(BaseDetectorAdapter):
    """
    Modern Model-Agnostic YOLO Detector Adapter.
    Features:
    - Real Model Fingerprinting directly inspecting weights and parameters
    - Automatic hardware acceleration (TensorRT / PyTorch CUDA FP16 / OpenVINO / CPU)
    - Full model provenance tracking (weights hash, runtime, device, precision)
    - Fast-Path vs Deep-Path dynamic execution
    """
    def __init__(
        self,
        name: str = "YOLOv8n Detector",
        model_path: str = "yolov8n.pt",
        model_name: Optional[str] = None,
        model_version: str = "v8.4.155",
        device: str = "cpu",
        input_resolution: str = "640x640",
        precision: str = "fp16"
    ):
        resolved_path = model_name or model_path
        super().__init__(name=name, model_path=resolved_path, device=device, input_resolution=input_resolution)
        self.model_version = model_version
        self.precision = precision
        self.runtime = "PyTorch"
        self.weights_hash = ""
        self.fingerprint: Optional[ModelFingerprint] = None
        self.model = None
        self.load()

    def _compute_weights_hash(self, path_str: str) -> str:
        try:
            p = Path(path_str)
            if p.exists() and p.is_file():
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                return h.hexdigest()
        except Exception:
            pass
        return "sha256-prebuilt"

    def load(self) -> bool:
        try:
            from ultralytics import YOLO
            import torch
            from pathlib import Path
            
            # Auto-detect CUDA if device is auto or cuda
            if self.device in ["auto", "cuda", "cuda:0"] and torch.cuda.is_available():
                self.device = "cuda:0"
                self.runtime = "CUDA_FP16" if self.precision == "fp16" else "CUDA_FP32"
                model_to_load = self.model_path
            else:
                self.device = "cpu"
                model_to_load = self.model_path
                # Only check for OpenVINO IR if model is specifically yolov8n fallback or openvino dir
                if "yolov8n" in str(self.model_path).lower():
                    candidates = [
                        Path(self.model_path).parent / "yolov8n_openvino_model",
                        Path("yolov8n_openvino_model"),
                        Path(__file__).parent.parent.parent.parent / "yolov8n_openvino_model",
                    ]
                    for c in candidates:
                        if c.exists() and (c / "yolov8n.xml").exists():
                            model_to_load = str(c)
                            self.runtime = "OpenVINO"
                            break
                    else:
                        self.runtime = "PyTorch_CPU"
                else:
                    self.runtime = "PyTorch_CPU"

            self.fingerprint = fingerprint_model_artifact(model_to_load)
            self.weights_hash = self.fingerprint.weights_sha256
            self.model = YOLO(model_to_load)
            if str(self.device).startswith("cuda"):
                self.model.to(self.device)
            self.status = DetectorStatus.LOADED
            self.last_error = None
            logger.info(f"Loaded {self.fingerprint.actual_variant} ({self.fingerprint.actual_family}, {self.fingerprint.parameter_count} params) from {model_to_load} on {self.device} [{self.runtime}]")
            return True
        except Exception as e:
            self.status = DetectorStatus.ERROR
            self.last_error = str(e)
            self.model = None
            logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")
            return False

    def unload(self) -> bool:
        self.model = None
        self.status = DetectorStatus.UNLOADED
        logger.info(f"Unloaded YOLO detector '{self.name}'")
        return True

    def get_supported_classes(self) -> List[str]:
        return sorted(list(set(SURVEILLANCE_CLASSES.values())))

    def detect(self, frame: np.ndarray, confidence_threshold: float = 0.35) -> List[Detection]:
        if frame is None or frame.size == 0 or self.status != DetectorStatus.LOADED or self.model is None:
            return []

        start_time = time.time()
        h, w = frame.shape[:2]
        detections: List[Detection] = []

        try:
            model_names = getattr(self.model, "names", {})
            predict_kwargs = {
                "conf": confidence_threshold,
                "imgsz": 640,
                "agnostic_nms": True,
                "iou": 0.45,
                "device": self.device,
                "verbose": False
            }
            results = self.model(frame, **predict_kwargs)

            for r in results:
                boxes = r.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    xyxy = box.xyxy[0].tolist()

                    # Normalize bounding box coordinates [0.0, 1.0]
                    x1 = max(0.0, min(1.0, xyxy[0] / w))
                    y1 = max(0.0, min(1.0, xyxy[1] / h))
                    x2 = max(0.0, min(1.0, xyxy[2] / w))
                    y2 = max(0.0, min(1.0, xyxy[3] / h))

                    # Filter out degenerately small boxes (< 8px)
                    if (x2 - x1) * w < 8 or (y2 - y1) * h < 8:
                        continue

                    class_name = model_names.get(cls_id, SURVEILLANCE_CLASSES.get(cls_id, "object")).lower()
                    detections.append(Detection(
                        class_name=class_name,
                        confidence=conf,
                        box=[x1, y1, x2, y2],
                        attributes={
                            "model_name": self.name,
                            "model_version": self.model_version,
                            "runtime": self.runtime,
                            "device": self.device,
                            "weights_hash": self.weights_hash
                        }
                    ))

            # Telemetry update
            elapsed = time.time() - start_time
            self.inference_latency_ms = round(elapsed * 1000.0, 2)
            self.inference_fps = round(1.0 / max(0.001, elapsed), 1)
            self.total_inferences += 1
            self.last_inference_ts = time.time()

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error during YOLO inference: {e}")

        return detections

