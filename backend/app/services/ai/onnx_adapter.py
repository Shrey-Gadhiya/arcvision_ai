import time
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import cv2

from app.services.ai.base import BaseDetectorAdapter, Detection, DetectorStatus

logger = logging.getLogger("arc_vision.onnx_adapter")

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book",
    "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

TARGET_SURVEILLANCE_CLASSES = {"person", "bicycle", "car", "motorcycle", "bus", "truck", "backpack", "dog", "cat"}

class ONNXDetectorAdapter(BaseDetectorAdapter):
    def __init__(
        self,
        name: str = "ONNX Runtime Detector",
        model_path: str = "yolov8n.onnx",
        device: str = "cpu",
        input_resolution: str = "640x640"
    ):
        super().__init__(name=name, model_path=model_path, device=device, input_resolution=input_resolution)
        self.session = None
        self.input_name = None
        self.input_shape = [1, 3, 640, 640]
        self.output_names = []
        self.load()

    def load(self) -> bool:
        try:
            import onnxruntime as ort
        except ImportError:
            self.status = DetectorStatus.NOT_SUPPORTED
            self.last_error = "onnxruntime package is not installed."
            logger.warning("ONNX Runtime not installed. ONNX detector adapter unavailable.")
            return False

        if not os.path.exists(self.model_path):
            self.status = DetectorStatus.ERROR
            self.last_error = f"ONNX model file not found at: {self.model_path}"
            logger.info(f"ONNX model file not found at: {self.model_path} (Standby mode)")
            return False

        try:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.device.lower() != 'cpu' else ['CPUExecutionProvider']
            # Fallback to available providers
            available = ort.get_available_providers()
            providers = [p for p in providers if p in available] or ['CPUExecutionProvider']

            self.session = ort.InferenceSession(self.model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape
            self.output_names = [o.name for o in self.session.get_outputs()]
            self.status = DetectorStatus.LOADED
            self.last_error = None
            logger.info(f"Loaded ONNX detector '{self.name}' on {providers[0]}")
            return True
        except Exception as e:
            self.status = DetectorStatus.ERROR
            self.last_error = str(e)
            self.session = None
            logger.error(f"Failed to load ONNX model {self.model_path}: {e}")
            return False

    def unload(self) -> bool:
        self.session = None
        self.status = DetectorStatus.UNLOADED
        return True

    def get_supported_classes(self) -> List[str]:
        return sorted(list(TARGET_SURVEILLANCE_CLASSES))

    def _letterbox(self, img: np.ndarray, target_size: int = 640) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        from typing import Tuple
        shape = img.shape[:2]  # [h, w]
        r = min(target_size / shape[0], target_size / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw, dh = target_size - new_unpad[0], target_size - new_unpad[1]
        dw /= 2
        dh /= 2

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, r, (dw, dh)

    def detect(self, frame: np.ndarray, confidence_threshold: float = 0.35) -> List[Detection]:
        if frame is None or frame.size == 0 or self.status != DetectorStatus.LOADED or self.session is None:
            return []

        start_time = time.time()
        orig_h, orig_w = frame.shape[:2]
        detections: List[Detection] = []

        try:
            target_size = 640
            try:
                target_size = int(self.input_resolution.split("x")[0])
            except Exception:
                target_size = 640

            # Preprocessing
            img, ratio, (dw, dh) = self._letterbox(frame, target_size=target_size)
            blob = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            blob = blob.transpose((2, 0, 1)).astype(np.float32) / 255.0
            blob = np.expand_dims(blob, axis=0)

            # Inference
            outputs = self.session.run(self.output_names, {self.input_name: blob})
            output = outputs[0]  # Shape e.g. [1, 84, 8400]

            if output.shape[1] < output.shape[2]:
                output = output.transpose(0, 2, 1) # [1, 8400, 84]

            predictions = output[0]
            boxes = []
            confidences = []
            class_ids = []

            for row in predictions:
                scores = row[4:]
                cls_id = int(np.argmax(scores))
                conf = float(scores[cls_id])
                if conf >= confidence_threshold:
                    class_name = COCO_CLASSES[cls_id] if cls_id < len(COCO_CLASSES) else "unknown"
                    if class_name in TARGET_SURVEILLANCE_CLASSES:
                        xc, yc, w, h = row[0], row[1], row[2], row[3]
                        # Undo letterboxing
                        x1 = (xc - w / 2 - dw) / ratio
                        y1 = (yc - h / 2 - dh) / ratio
                        x2 = (xc + w / 2 - dw) / ratio
                        y2 = (yc + h / 2 - dh) / ratio

                        boxes.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
                        confidences.append(float(conf))
                        class_ids.append(cls_id)

            # Non-Maximum Suppression (NMS)
            indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, 0.45)
            if len(indices) > 0:
                for idx in indices.flatten():
                    bx, by, bw, bh = boxes[idx]
                    cls_id = class_ids[idx]
                    conf = confidences[idx]
                    c_name = COCO_CLASSES[cls_id] if cls_id < len(COCO_CLASSES) else "unknown"

                    # Normalize bounding box
                    nx1 = max(0.0, min(1.0, bx / orig_w))
                    ny1 = max(0.0, min(1.0, by / orig_h))
                    nx2 = max(0.0, min(1.0, (bx + bw) / orig_w))
                    ny2 = max(0.0, min(1.0, (by + bh) / orig_h))

                    detections.append(Detection(
                        class_name=c_name,
                        confidence=conf,
                        box=[nx1, ny1, nx2, ny2]
                    ))

            elapsed = time.time() - start_time
            self.inference_latency_ms = round(elapsed * 1000.0, 2)
            self.inference_fps = round(1.0 / max(0.001, elapsed), 1)
            self.total_inferences += 1
            self.last_inference_ts = time.time()

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error during ONNX inference: {e}")

        return detections
