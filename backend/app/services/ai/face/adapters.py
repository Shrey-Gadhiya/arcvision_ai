import os
import time
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from app.services.ai.face.base import (
    BaseFaceDetectorAdapter,
    BaseFaceEmbeddingAdapter,
    AdapterStatus,
    FaceDetectionResult,
    FaceEmbeddingResult,
)
from app.services.ai.face.quality import FaceQualityChecker

from pathlib import Path
from app.core.config import settings

def _resolve_model_path(filename: str, custom_path: Optional[str] = None) -> str:
    if custom_path and os.path.exists(custom_path):
        return str(Path(custom_path).resolve())
    clean_fn = Path(filename).name
    candidates = [
        settings.MODELS_DIR / clean_fn,
        settings.MODELS_DIR / "face" / clean_fn,
        Path("data/models") / clean_fn,
        Path("data/models/face") / clean_fn,
        Path("backend/data/models") / clean_fn,
        Path("backend/data/models/face") / clean_fn,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "models" / clean_fn,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "models" / "face" / clean_fn,
        Path("/content/ARCVISION/backend/data/models") / clean_fn,
        Path("/kaggle/working/ARCVISION/backend/data/models") / clean_fn,
    ]
    for c in candidates:
        try:
            if c and c.exists() and c.is_file() and c.stat().st_size > 0:
                return str(c.resolve())
        except Exception:
            pass
    return str((settings.MODELS_DIR / clean_fn).resolve())

class YuNetFaceDetectorAdapter(BaseFaceDetectorAdapter):
    """
    Production ONNX-compatible Face Detector using OpenCV YuNet (FaceDetectorYN).
    Detects bounding boxes, confidence, 5 facial landmarks (eyes, nose, mouth corners),
    and computes quality metrics.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        input_size: tuple = (320, 320),
        score_threshold: float = 0.50,
        nms_threshold: float = 0.30,
        top_k: int = 500
    ):
        super().__init__(name="YuNet-ONNX-Detector", device=device)
        self.model_path = _resolve_model_path("face_detection_yunet_2023mar.onnx", model_path or os.getenv("FACE_DETECTOR_MODEL_PATH"))
        self.input_size = input_size
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.top_k = top_k
        self.detector = None
        self.quality_checker = FaceQualityChecker()

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            self.status = AdapterStatus.NOT_CONFIGURED
            self.last_error = f"YuNet ONNX model weight file not found at: {self.model_path}"
            return False

        try:
            try:
                backend_id = cv2.dnn.DNN_BACKEND_OPENCV
                target_id = cv2.dnn.DNN_TARGET_CPU
                if self.device == "cuda" or str(self.device).startswith("cuda"):
                    backend_id = cv2.dnn.DNN_BACKEND_CUDA
                    target_id = cv2.dnn.DNN_TARGET_CUDA
                self.detector = cv2.FaceDetectorYN.create(
                    model=self.model_path,
                    config="",
                    input_size=self.input_size,
                    score_threshold=self.score_threshold,
                    nms_threshold=self.nms_threshold,
                    top_k=self.top_k,
                    backend_id=backend_id,
                    target_id=target_id
                )
            except Exception:
                # Fallback to OpenCV CPU
                self.detector = cv2.FaceDetectorYN.create(
                    model=self.model_path,
                    config="",
                    input_size=self.input_size,
                    score_threshold=self.score_threshold,
                    nms_threshold=self.nms_threshold,
                    top_k=self.top_k,
                    backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                    target_id=cv2.dnn.DNN_TARGET_CPU
                )
            self.status = AdapterStatus.LOADED
            self.last_error = None
            return True
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.last_error = f"Failed to load YuNet detector: {str(e)}"
            return False

    def unload(self) -> bool:
        self.detector = None
        self.status = AdapterStatus.UNLOADED
        return True

    def detect_faces(self, image: np.ndarray, confidence_threshold: float = 0.50) -> List[FaceDetectionResult]:
        if self.status != AdapterStatus.LOADED or self.detector is None:
            return []

        if image is None or image.size == 0:
            return []

        start_t = time.time()
        img_h, img_w = image.shape[:2]

        try:
            # Set dynamic input size to match frame
            self.detector.setInputSize((img_w, img_h))
            self.detector.setScoreThreshold(confidence_threshold)
            _, faces = self.detector.detect(image)

            dur = (time.time() - start_t) * 1000.0
            self.latency_ms = dur
            self.fps = 1000.0 / max(1.0, dur)

            results: List[FaceDetectionResult] = []
            if faces is not None:
                for face in faces:
                    # face format: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
                    x, y, w, h = face[0:4]
                    score = float(face[-1])
                    if score < confidence_threshold:
                        continue

                    # Bounding box relative coordinates [x1, y1, x2, y2]
                    x1 = max(0.0, float(x) / img_w)
                    y1 = max(0.0, float(y) / img_h)
                    x2 = min(1.0, float(x + w) / img_w)
                    y2 = min(1.0, float(y + h) / img_h)

                    # Extract landmark coords
                    landmarks = []
                    if len(face) >= 15:
                        for i in range(4, 14, 2):
                            landmarks.append([float(face[i]) / img_w, float(face[i+1]) / img_h])

                    # Extract face crop
                    px_x1 = max(0, int(x))
                    px_y1 = max(0, int(y))
                    px_x2 = min(img_w, int(x + w))
                    px_y2 = min(img_h, int(y + h))

                    face_crop = None
                    if px_x2 > px_x1 and px_y2 > px_y1:
                        face_crop = image[px_y1:px_y2, px_x1:px_x2].copy()

                    quality_score, sharpness, _ = self.quality_checker.evaluate_face_crop(face_crop)

                    results.append(FaceDetectionResult(
                        box=[x1, y1, x2, y2],
                        confidence=score,
                        landmarks=landmarks,
                        face_crop=face_crop,
                        quality_score=quality_score,
                        sharpness_score=sharpness
                    ))

            self.total_detections += len(results)
            return results
        except Exception as e:
            self.last_error = f"YuNet detection exception: {str(e)}"
            return []


class UnavailableFaceDetectorAdapter(BaseFaceDetectorAdapter):
    """
    Fallback Face Detector adapter when no neural detector weights are configured.
    Explicitly reports NOT_CONFIGURED without fabricating face detections.
    """

    def __init__(self, reason: str = "No face detector model weights configured"):
        super().__init__(name="UnavailableFaceDetector", device="cpu")
        self.status = AdapterStatus.NOT_CONFIGURED
        self.last_error = reason

    def load(self) -> bool:
        self.status = AdapterStatus.NOT_CONFIGURED
        return False

    def unload(self) -> bool:
        return True

    def detect_faces(self, image: np.ndarray, confidence_threshold: float = 0.50) -> List[FaceDetectionResult]:
        return []


class SFaceEmbeddingAdapter(BaseFaceEmbeddingAdapter):
    """
    Production ONNX Face Embedding Model using OpenCV SFace (FaceRecognizerSF) or MobileFaceNet.
    Generates 128-d or 512-d L2-normalized face embeddings.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        dimension: int = 128
    ):
        super().__init__(name="SFace-ONNX-Recognizer", device=device, dimension=dimension)
        self.model_path = _resolve_model_path("face_recognition_sface_2021dec.onnx", model_path or os.getenv("FACE_EMBEDDING_MODEL_PATH"))
        self.recognizer = None

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            self.status = AdapterStatus.NOT_CONFIGURED
            self.last_error = f"SFace ONNX model weight file not found at: {self.model_path}"
            return False

        try:
            backend_id = cv2.dnn.DNN_BACKEND_OPENCV
            target_id = cv2.dnn.DNN_TARGET_CPU
            if self.device == "cuda":
                backend_id = cv2.dnn.DNN_BACKEND_CUDA
                target_id = cv2.dnn.DNN_TARGET_CUDA

            self.recognizer = cv2.FaceRecognizerSF.create(
                model=self.model_path,
                config="",
                backend_id=backend_id,
                target_id=target_id
            )
            self.status = AdapterStatus.LOADED
            self.last_error = None
            return True
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.last_error = f"Failed to load SFace recognizer: {str(e)}"
            return False

    def unload(self) -> bool:
        self.recognizer = None
        self.status = AdapterStatus.UNLOADED
        return True

    def compute_embedding(self, face_crop: np.ndarray) -> FaceEmbeddingResult:
        if self.status != AdapterStatus.LOADED or self.recognizer is None:
            return FaceEmbeddingResult(
                embedding=None,
                dimension=0,
                status="NOT_CONFIGURED",
                metadata={"error": self.last_error or "Model not loaded"}
            )

        if face_crop is None or face_crop.size == 0:
            return FaceEmbeddingResult(
                embedding=None,
                dimension=0,
                status="ERROR",
                metadata={"error": "Empty face crop"}
            )

        start_t = time.time()
        try:
            # OpenCV SFace feature extraction:
            # SFace expects 112x112 aligned image
            resized = cv2.resize(face_crop, (112, 112))
            feature = self.recognizer.feature(resized)
            raw_vec = feature[0].tolist()

            # Normalize embedding vector with L2 norm
            vec_np = np.array(raw_vec, dtype=np.float32)
            norm = np.linalg.norm(vec_np)
            if norm > 0:
                vec_np = vec_np / norm
            norm_vec = vec_np.tolist()

            dur = (time.time() - start_t) * 1000.0
            self.latency_ms = dur
            self.total_embeddings += 1

            return FaceEmbeddingResult(
                embedding=norm_vec,
                dimension=len(norm_vec),
                normalized=True,
                status="SUCCESS",
                metadata={"latency_ms": round(dur, 2)}
            )
        except Exception as e:
            return FaceEmbeddingResult(
                embedding=None,
                dimension=0,
                status="ERROR",
                metadata={"error": str(e)}
            )


class UnavailableFaceEmbeddingAdapter(BaseFaceEmbeddingAdapter):
    """
    Fallback Face Embedding adapter when no recognition model weights are configured.
    Explicitly reports NOT_CONFIGURED without fabricating recognition results.
    """

    def __init__(self, reason: str = "No face embedding model weights configured"):
        super().__init__(name="UnavailableFaceEmbedding", device="cpu", dimension=0)
        self.status = AdapterStatus.NOT_CONFIGURED
        self.last_error = reason

    def load(self) -> bool:
        self.status = AdapterStatus.NOT_CONFIGURED
        return False

    def unload(self) -> bool:
        return True

    def compute_embedding(self, face_crop: np.ndarray) -> FaceEmbeddingResult:
        return FaceEmbeddingResult(
            embedding=None,
            dimension=0,
            status="NOT_CONFIGURED",
            metadata={"error": self.last_error}
        )
