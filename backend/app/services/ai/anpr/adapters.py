import os
import time
import logging
import cv2
import numpy as np
from typing import List, Optional, Dict, Any, Tuple

from app.services.ai.anpr.base import (
    BasePlateDetectorAdapter,
    BasePlateOCRAdapter,
    PlateDetectionResult,
    OCRResult,
    AdapterStatus
)
from app.services.ai.anpr.normalizer import clean_raw_plate

logger = logging.getLogger("arc_vision.anpr.adapters")

BANNED_PLATE_WORDS = {
    "SCANNING", "PLATESCANNING", "SCAN", "PLATE", "CAMERA", "FPS", "SECURITY", 
    "DETECTED", "MOTION", "TRACK", "VEHICLE", "ALERT", "SPEED", "LIVE"
}

def is_valid_plate_candidate(cleaned_text: str) -> bool:
    if not cleaned_text or len(cleaned_text) < 3:
        return False
    upper = cleaned_text.upper()
    if upper in BANNED_PLATE_WORDS:
        return False
    for banned in ("SCANNING", "PLATESCAN", "CAMERAFPS"):
        if banned in upper:
            return False
    return True

class HeuristicPlateDetectorAdapter(BasePlateDetectorAdapter):
    """
    Adaptive heuristic plate detector.
    Localizes plate region in vehicle crop using contrast enhancement and lower-third ROI geometry.
    """
    def __init__(self, name: str = "heuristic_plate_detector", device: str = "cpu"):
        super().__init__(name=name, device=device)
        self.status = AdapterStatus.LOADED

    def load(self) -> bool:
        self.status = AdapterStatus.LOADED
        return True

    def unload(self) -> bool:
        self.status = AdapterStatus.UNLOADED
        return True

    def detect_plates(self, vehicle_crop: np.ndarray, confidence_threshold: float = 0.40) -> List[PlateDetectionResult]:
        if vehicle_crop is None or vehicle_crop.size == 0:
            return []

        t0 = time.time()
        h, w = vehicle_crop.shape[:2]
        if h < 20 or w < 20:
            return []

        # Standard CCTV vehicle plate ROI: bottom 45% of vehicle bounding box, centered 80% horizontally
        y1_rel = 0.50
        y2_rel = 0.95
        x1_rel = 0.10
        x2_rel = 0.90

        y1 = int(h * y1_rel)
        y2 = int(h * y2_rel)
        x1 = int(w * x1_rel)
        x2 = int(w * x2_rel)

        plate_crop = vehicle_crop[y1:y2, x1:x2]
        if plate_crop.size == 0:
            plate_crop = vehicle_crop

        self.latency_ms = (time.time() - t0) * 1000.0
        self.total_detections += 1

        result = PlateDetectionResult(
            box=[x1_rel, y1_rel, x2_rel, y2_rel],
            confidence=0.85,
            plate_crop=plate_crop
        )
        return [result]

class EasyOCRPlateAdapter(BasePlateOCRAdapter):
    """Production EasyOCR adapter for vehicle license plates."""
    def __init__(self, name: str = "easyocr_plate_reader", device: str = "cpu"):
        super().__init__(name=name, device=device)
        self.reader = None

    def load(self) -> bool:
        try:
            import easyocr
            use_gpu = self.device.lower() in ("cuda", "gpu")
            self.reader = easyocr.Reader(['en'], gpu=use_gpu, verbose=False)
            self.status = AdapterStatus.LOADED
            self.last_error = None
            logger.info(f"EasyOCR adapter successfully initialized on {self.device}.")
            return True
        except ImportError:
            self.status = AdapterStatus.UNAVAILABLE
            self.last_error = "easyocr package is not installed in the environment"
            logger.warning(f"EasyOCR unavailable: {self.last_error}")
            return False
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Failed to load EasyOCR: {e}")
            return False

    def unload(self) -> bool:
        self.reader = None
        self.status = AdapterStatus.UNLOADED
        return True

    def preprocess_plate(self, crop: np.ndarray) -> np.ndarray:
        if crop is None or crop.size == 0:
            return crop
        h, w = crop.shape[:2]
        # If crop is low resolution (e.g. distant vehicle), upscale using cubic interpolation
        if h < 90 or w < 220:
            scale = max(1.5, min(3.0, 160.0 / max(1, h)))
            crop = cv2.resize(crop, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)
        filtered = cv2.bilateralFilter(contrast, 9, 75, 75)
        return filtered

    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        if self.status != AdapterStatus.LOADED or self.reader is None:
            return OCRResult(
                raw_text="",
                confidence=0.0,
                status=self.status.value,
                metadata={"error": self.last_error or "EasyOCR not loaded"}
            )

        if plate_crop is None or plate_crop.size == 0:
            return OCRResult(raw_text="", confidence=0.0, status="EMPTY_IMAGE")

        t0 = time.time()
        try:
            processed = self.preprocess_plate(plate_crop)
            results = self.reader.readtext(processed)
            self.latency_ms = (time.time() - t0) * 1000.0
            self.total_reads += 1

            best_text = ""
            best_conf = 0.0
            best_box = None

            for (bbox, text, conf) in results:
                cleaned = clean_raw_plate(text)
                if is_valid_plate_candidate(cleaned) and len(cleaned) >= 4 and float(conf) > best_conf:
                    best_text = cleaned
                    best_conf = float(conf)
                    try:
                        pts = np.array(bbox, dtype=np.int32)
                        xmin, ymin = int(np.min(pts[:, 0])), int(np.min(pts[:, 1]))
                        xmax, ymax = int(np.max(pts[:, 0])), int(np.max(pts[:, 1]))
                        best_box = [xmin, ymin, xmax, ymax]
                    except Exception:
                        best_box = None

            return OCRResult(
                raw_text=best_text,
                confidence=round(float(best_conf), 3),
                status="SUCCESS" if best_text else "NO_TEXT_DETECTED",
                metadata={"raw_candidates": len(results), "box": best_box}
            )
        except Exception as e:
            self.latency_ms = (time.time() - t0) * 1000.0
            return OCRResult(
                raw_text="",
                confidence=0.0,
                status="ERROR",
                metadata={"error": str(e)}
            )

    def detect_and_read_from_frame(self, frame_or_crop: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Strong multi-pass neural OCR & plate detection.
        1. Runs multi-pass inference (Standard RGB + CLAHE/Bilateral + Morphological High-Contrast).
        2. Detects all text bounding boxes, merges vertically/horizontally stacked plate lines (e.g. HR 26 + DD 2911).
        3. Localizes precise target square [xmin, ymin, xmax, ymax] and extracts normalized license plate.
        """
        if self.status != AdapterStatus.LOADED or self.reader is None or frame_or_crop is None or frame_or_crop.size == 0:
            return None

        t0 = time.time()
        h, w = frame_or_crop.shape[:2]

        def _run_ocr_pass(img: np.ndarray):
            try:
                return self.reader.readtext(img)
            except Exception:
                return []

        # Pass 1: Standard frame
        results = _run_ocr_pass(frame_or_crop)

        # Pass 2: If no strong result, run CLAHE + Bilateral
        if not results or not any(is_valid_plate_candidate(clean_raw_plate(t)) for _, t, _ in results):
            proc_clahe = self.preprocess_plate(frame_or_crop)
            res2 = _run_ocr_pass(proc_clahe)
            if res2:
                results = res2

        # Pass 3: Morphological high-contrast thresholding for tough low-light / reflective plates
        if not results or not any(is_valid_plate_candidate(clean_raw_plate(t)) for _, t, _ in results):
            gray = cv2.cvtColor(frame_or_crop, cv2.COLOR_BGR2GRAY) if len(frame_or_crop.shape) == 3 else frame_or_crop
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
            blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
            enhanced = cv2.addWeighted(gray, 0.7, blackhat, 0.3, 0)
            res3 = _run_ocr_pass(enhanced)
            if res3:
                results = res3

        # Pass 4: Adaptive Gaussian Thresholding (detects white-on-black and black-on-white plates)
        if not results or not any(is_valid_plate_candidate(clean_raw_plate(t)) for _, t, _ in results):
            gray_im = cv2.cvtColor(frame_or_crop, cv2.COLOR_BGR2GRAY) if len(frame_or_crop.shape) == 3 else frame_or_crop
            blur = cv2.GaussianBlur(gray_im, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 19, 9)
            res4 = _run_ocr_pass(thresh)
            if res4:
                results = res4

        self.latency_ms = (time.time() - t0) * 1000.0

        if not results:
            return None

        # Parse and collect text fragments with coordinates
        parsed_items = []
        for (bbox, text, conf) in results:
            cleaned = clean_raw_plate(text)
            if is_valid_plate_candidate(cleaned) and len(cleaned) >= 2:
                pts = np.array(bbox, dtype=np.int32)
                xmin = max(0, int(np.min(pts[:, 0])))
                ymin = max(0, int(np.min(pts[:, 1])))
                xmax = min(w, int(np.max(pts[:, 0])))
                ymax = min(h, int(np.max(pts[:, 1])))
                parsed_items.append({
                    "raw_text": text.strip(),
                    "cleaned": cleaned,
                    "conf": float(conf),
                    "box": [xmin, ymin, xmax, ymax],
                    "center_y": (ymin + ymax) / 2.0,
                    "center_x": (xmin + xmax) / 2.0
                })

        if not parsed_items:
            return None

        # Sort by vertical position (top to bottom) then horizontal (left to right)
        parsed_items.sort(key=lambda item: (item["center_y"] // 25, item["center_x"]))

        # Check if single line is already a complete plate (>= 4 chars)
        single_best = None
        for item in parsed_items:
            if len(item["cleaned"]) >= 4:
                if single_best is None or item["conf"] > single_best["conf"]:
                    single_best = item

        # Check for stacked 2-line or 3-line plates (common on bikes, scooters, and square plates)
        stitched_result = None
        if len(parsed_items) >= 2:
            # Check adjacent items in proximity
            for i in range(len(parsed_items) - 1):
                it1, it2 = parsed_items[i], parsed_items[i + 1]
                comb_cleaned = it1["cleaned"] + it2["cleaned"]
                if 4 <= len(comb_cleaned) <= 12:
                    u_xmin = min(it1["box"][0], it2["box"][0])
                    u_ymin = min(it1["box"][1], it2["box"][1])
                    u_xmax = max(it1["box"][2], it2["box"][2])
                    u_ymax = max(it1["box"][3], it2["box"][3])
                    box_w = u_xmax - u_xmin
                    box_h = u_ymax - u_ymin

                    if box_w > 8 and box_h > 8:
                        comb_conf = round(float((it1["conf"] + it2["conf"]) / 2.0), 3)
                        stitched_result = {
                            "raw_text": f"{it1['raw_text']} {it2['raw_text']}",
                            "cleaned_text": comb_cleaned,
                            "confidence": comb_conf,
                            "box": [u_xmin, u_ymin, u_xmax, u_ymax]
                        }
                        break

        # Select best candidate (prefer stitched two-line plate if single was short, or single if high conf)
        best_candidate = None
        if stitched_result and (not single_best or len(single_best["cleaned"]) < 7 or stitched_result["confidence"] >= single_best["conf"]):
            best_candidate = stitched_result
        elif single_best:
            best_candidate = {
                "raw_text": single_best["raw_text"],
                "cleaned_text": single_best["cleaned"],
                "confidence": round(float(single_best["conf"]), 3),
                "box": single_best["box"]
            }
        else:
            # Fallback to highest confidence chunk
            parsed_items.sort(key=lambda x: x["conf"], reverse=True)
            top = parsed_items[0]
            best_candidate = {
                "raw_text": top["raw_text"],
                "cleaned_text": top["cleaned"],
                "confidence": round(float(top["conf"]), 3),
                "box": top["box"]
            }

        # Compute padded plate crop
        xmin, ymin, xmax, ymax = best_candidate["box"]
        pad_x = max(6, int((xmax - xmin) * 0.12))
        pad_y = max(6, int((ymax - ymin) * 0.20))
        crop_xmin = max(0, xmin - pad_x)
        crop_ymin = max(0, ymin - pad_y)
        crop_xmax = min(w, xmax + pad_x)
        crop_ymax = min(h, ymax + pad_y)

        plate_crop = frame_or_crop[crop_ymin:crop_ymax, crop_xmin:crop_xmax]
        if plate_crop.size == 0:
            plate_crop = frame_or_crop

        best_candidate["plate_crop"] = plate_crop
        best_candidate["box_rel"] = [
            round(max(0.0, min(1.0, float(xmin) / max(1, w))), 4),
            round(max(0.0, min(1.0, float(ymin) / max(1, h))), 4),
            round(max(0.0, min(1.0, float(xmax) / max(1, w))), 4),
            round(max(0.0, min(1.0, float(ymax) / max(1, h))), 4)
        ]
        return best_candidate

from pathlib import Path
from app.core.config import settings

def _resolve_crnn_model_path(filename: str = "crnn_en_2021sep.onnx", custom_path: Optional[str] = None) -> str:
    if custom_path and os.path.exists(custom_path):
        return str(Path(custom_path).resolve())
    clean_fn = Path(filename).name
    candidates = [
        settings.MODELS_DIR / "ocr" / clean_fn,
        settings.MODELS_DIR / clean_fn,
        Path("data/models/ocr") / clean_fn,
        Path("data/models") / clean_fn,
        Path("backend/data/models/ocr") / clean_fn,
        Path("backend/data/models") / clean_fn,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "models" / "ocr" / clean_fn,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "models" / clean_fn,
        Path("/content/ARCVISION/backend/data/models/ocr") / clean_fn,
        Path("/content/ARCVISION/backend/data/models") / clean_fn,
        Path("/kaggle/working/ARCVISION/backend/data/models/ocr") / clean_fn,
        Path("/kaggle/working/ARCVISION/backend/data/models") / clean_fn,
    ]
    for c in candidates:
        try:
            if c and c.exists() and c.is_file() and c.stat().st_size > 0:
                return str(c.resolve())
        except Exception:
            pass
    return str((settings.MODELS_DIR / "ocr" / clean_fn).resolve())

class CRNNPlateOCRAdapter(BasePlateOCRAdapter):
    """
    Real Neural CRNN Plate OCR Adapter using OpenCV DNN and CTC Decoding.
    Artifact: data/models/ocr/crnn_en_2021sep.onnx (33.8 MB, 37 CTC classes).
    """
    VOCABULARY = "0123456789abcdefghijklmnopqrstuvwxyz"

    def __init__(
        self,
        name: str = "crnn_plate_ocr",
        model_path: Optional[str] = None,
        device: str = "cpu"
    ):
        super().__init__(name=name, device=device)
        self.model_path = _resolve_crnn_model_path("crnn_en_2021sep.onnx", model_path or os.getenv("CRNN_OCR_MODEL_PATH"))
        self.net = None
        self.load()

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            self.status = AdapterStatus.UNAVAILABLE
            self.last_error = f"CRNN model weights not found at {self.model_path}"
            logger.warning(self.last_error)
            return False
        try:
            self.net = cv2.dnn.readNetFromONNX(self.model_path)
            self.status = AdapterStatus.LOADED
            self.last_error = None
            logger.info(f"CRNN Plate OCR Adapter loaded successfully from {self.model_path} on {self.device}")
            return True
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Failed to load CRNN ONNX model: {e}")
            return False

    def unload(self) -> bool:
        self.net = None
        self.status = AdapterStatus.UNLOADED
        return True

    def _ctc_decode(self, preds: np.ndarray) -> Tuple[str, float]:
        """Greedy CTC decoding over sequence length (T, 1, C)."""
        # preds shape: (T, 1, 37)
        if len(preds.shape) == 3:
            preds = preds[:, 0, :]
        
        # Softmax over classes
        exp_preds = np.exp(preds - np.max(preds, axis=-1, keepdims=True))
        probs = exp_preds / np.sum(exp_preds, axis=-1, keepdims=True)
        
        best_indices = np.argmax(probs, axis=-1)
        confidences = np.max(probs, axis=-1)
        
        char_list = []
        conf_list = []
        prev_idx = -1
        
        blank_idx = len(self.VOCABULARY)  # index 36 is blank
        
        for idx, conf in zip(best_indices, confidences):
            if idx != prev_idx and idx < blank_idx:
                char_list.append(self.VOCABULARY[idx].upper())
                conf_list.append(float(conf))
            prev_idx = idx
            
        decoded_text = "".join(char_list)
        avg_conf = float(np.mean(conf_list)) if conf_list else 0.0
        return decoded_text, avg_conf

    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        if self.status != AdapterStatus.LOADED or self.net is None:
            return OCRResult(
                raw_text="",
                confidence=0.0,
                status=self.status.value,
                metadata={"error": self.last_error or "CRNN net not loaded"}
            )
        if plate_crop is None or plate_crop.size == 0:
            return OCRResult(raw_text="", confidence=0.0, status="EMPTY_IMAGE")

        t0 = time.time()
        try:
            h, w = plate_crop.shape[:2]
            target_w = max(100, int(w * (32.0 / max(1, h))))
            # Construct blob
            blob = cv2.dnn.blobFromImage(
                plate_crop,
                scalefactor=1.0 / 127.5,
                size=(target_w, 32),
                mean=(127.5, 127.5, 127.5),
                swapRB=True,
                crop=False
            )
            self.net.setInput(blob)
            preds = self.net.forward()
            text, conf = self._ctc_decode(preds)
            cleaned = clean_raw_plate(text)
            self.latency_ms = (time.time() - t0) * 1000.0
            
            return OCRResult(
                raw_text=cleaned,
                confidence=round(conf, 3),
                status="SUCCESS" if cleaned else "NO_TEXT",
                metadata={"raw": text, "latency_ms": round(self.latency_ms, 2)}
            )
        except Exception as e:
            self.latency_ms = (time.time() - t0) * 1000.0
            return OCRResult(raw_text="", confidence=0.0, status="ERROR", metadata={"error": str(e)})

    def detect_and_read_from_frame(self, frame_or_crop: np.ndarray) -> Optional[Dict[str, Any]]:
        """Multi-pass CRNN neural inference over vehicle crop ROIs."""
        if self.status != AdapterStatus.LOADED or self.net is None or frame_or_crop is None or frame_or_crop.size == 0:
            return None
        h, w = frame_or_crop.shape[:2]
        # Evaluate lower-half ROI where vehicle license plates are mounted
        y_start = int(h * 0.35) if h > 50 else 0
        roi = frame_or_crop[y_start:h, :]
        if roi.size == 0:
            roi = frame_or_crop
            y_start = 0

        res = self.read_plate(roi)
        if not res.raw_text or len(res.raw_text) < 3 or res.confidence < 0.20:
            # Fallback: Evaluate full vehicle crop
            res = self.read_plate(frame_or_crop)
            y_start = 0

        if res.raw_text and len(res.raw_text) >= 3 and res.confidence >= 0.20:
            box = [0, y_start, w, h]
            return {
                "raw_text": res.metadata.get("raw", res.raw_text),
                "cleaned_text": res.raw_text,
                "confidence": res.confidence,
                "box": box,
                "plate_crop": roi if y_start > 0 else frame_or_crop,
                "box_rel": [0.0, float(y_start) / max(1, h), 1.0, 1.0]
            }
        return None

class UnavailablePlateDetectorAdapter(BasePlateDetectorAdapter):
    """Explicit adapter indicating plate detection model is not configured."""
    def __init__(self, name: str = "unavailable_plate_detector"):
        super().__init__(name=name, device="none")
        self.status = AdapterStatus.NOT_CONFIGURED
        self.last_error = "Plate detector model not configured"

    def load(self) -> bool:
        return False

    def unload(self) -> bool:
        return True

    def detect_plates(self, vehicle_crop: np.ndarray, confidence_threshold: float = 0.40) -> List[PlateDetectionResult]:
        return []

class UnavailableOCRAdapter(BasePlateOCRAdapter):
    """Explicit adapter indicating OCR engine is not configured/installed."""
    def __init__(self, name: str = "unavailable_ocr_engine"):
        super().__init__(name=name, device="none")
        self.status = AdapterStatus.UNAVAILABLE
        self.last_error = "No OCR engine loaded. Install easyocr or configure ONNX OCR."

    def load(self) -> bool:
        return False

    def unload(self) -> bool:
        return True

    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        return OCRResult(
            raw_text="",
            confidence=0.0,
            status=AdapterStatus.UNAVAILABLE.value,
            metadata={"detail": "OCR engine unavailable. No synthetic plate generated."}
        )
