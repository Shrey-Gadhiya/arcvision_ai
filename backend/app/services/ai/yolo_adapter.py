import time
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from app.services.ai.base import BaseDetectorAdapter, Detection, DetectorStatus

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
    def __init__(
        self,
        name: str = "YOLOv8n Detector",
        model_path: str = "yolov8n.pt",
        model_name: Optional[str] = None,
        device: str = "cpu",
        input_resolution: str = "640x640"
    ):
        resolved_path = model_name or model_path
        super().__init__(name=name, model_path=resolved_path, device=device, input_resolution=input_resolution)
        self.model = None
        self.load()

    def load(self) -> bool:
        try:
            from ultralytics import YOLO
            import torch
            from pathlib import Path
            
            # Auto-detect CUDA if device is auto or cuda
            if self.device in ["auto", "cuda", "cuda:0"] and torch.cuda.is_available():
                self.device = "cuda:0"
                model_to_load = self.model_path
            else:
                self.device = "cpu"
                # Check for high-performance Intel/AMD OpenVINO model
                candidates = [
                    Path(self.model_path).parent / "yolov8n_openvino_model",
                    Path("yolov8n_openvino_model"),
                    Path(__file__).parent.parent.parent.parent / "yolov8n_openvino_model",
                ]
                model_to_load = self.model_path
                for c in candidates:
                    if c.exists() and (c / "yolov8n.xml").exists():
                        model_to_load = str(c)
                        break

            self.model = YOLO(model_to_load)
            self.status = DetectorStatus.LOADED
            self.last_error = None
            logger.info(f"Successfully loaded YOLO detector '{self.name}' from {model_to_load} on {self.device}")
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
            results = self.model(
                frame,
                conf=confidence_threshold,
                classes=list(SURVEILLANCE_CLASSES.keys()),
                imgsz=640,
                agnostic_nms=True,
                iou=0.45,
                device=self.device,
                verbose=False
            )

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

                    class_name = SURVEILLANCE_CLASSES.get(cls_id, "unknown")
                    detections.append(Detection(
                        class_name=class_name,
                        confidence=conf,
                        box=[x1, y1, x2, y2]
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
