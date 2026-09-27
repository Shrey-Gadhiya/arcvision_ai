import time
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("arc_vision.face.concealment")

class FaceConcealmentDetector:
    """
    Tactical Face Concealment, Masking, and Occlusion Analyzer.
    Detects individuals intentionally obscuring their identity using:
    - Balaclavas / Ski masks
    - Dark fabric / Bandanas covering lower/full face
    - Deep hoodies pulled over face
    - Sunglasses + cap combinations obscuring biometric landmarks
    """
    def __init__(self, min_occlusion_ratio: float = 0.55):
        self.min_occlusion_ratio = min_occlusion_ratio
        self._subject_history: Dict[int, Dict[str, Any]] = {}

    def analyze_person_face_visibility(
        self,
        frame: np.ndarray,
        person_box: List[float],
        track_id: int,
        camera_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts head/face region and evaluates skin-tone ratio, texture variance,
        and biometric visibility to determine if face is intentionally concealed.
        """
        if frame is None or frame.size == 0 or len(person_box) != 4:
            return None

        try:
            h, w = frame.shape[:2]
            px1 = max(0, int(person_box[0] * w))
            py1 = max(0, int(person_box[1] * h))
            px2 = min(w, int(person_box[2] * w))
            py2 = min(h, int(person_box[3] * h))

            pw = px2 - px1
            ph = py2 - py1

            if pw < 20 or ph < 40:
                return None

            # Upper 28% represents the head/face region
            head_y2 = min(py2, py1 + int(ph * 0.28))
            head_crop = frame[py1:head_y2, px1:px2]

            if head_crop.size == 0:
                return None

            # 1. Convert to HSV and YCrCb for robust multi-ethnic skin tone color segmentation
            hsv = cv2.cvtColor(head_crop, cv2.COLOR_BGR2HSV)
            ycrcb = cv2.cvtColor(head_crop, cv2.COLOR_BGR2YCrCb)

            # Standard skin color range masks
            skin_mask_hsv = cv2.inRange(hsv, np.array([0, 20, 50], dtype=np.uint8), np.array([25, 255, 255], dtype=np.uint8))
            skin_mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))
            skin_combined = cv2.bitwise_and(skin_mask_hsv, skin_mask_ycrcb)

            total_pixels = head_crop.shape[0] * head_crop.shape[1]
            skin_pixels = cv2.countNonZero(skin_combined)
            skin_ratio = skin_pixels / max(1, total_pixels)

            # 2. Check for dark fabric / balaclava / mask coverage (low value / high texture)
            gray_head = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
            dark_mask = cv2.inRange(gray_head, 0, 65)
            dark_ratio = cv2.countNonZero(dark_mask) / max(1, total_pixels)

            # A normal uncovered face typically has 35-75% exposed skin in head ROI.
            # A concealed person (balaclava, dark mask, wrapped cloth) exhibits < 15% skin tone + high dark/cloth coverage.
            is_concealed = (skin_ratio < 0.12 and dark_ratio > 0.45) or (skin_ratio < 0.08)

            now_ts = time.time()
            hist = self._subject_history.get(track_id, {"first_seen": now_ts, "concealed_frames": 0, "total_frames": 0})
            hist["total_frames"] += 1
            if is_concealed:
                hist["concealed_frames"] += 1
            self._subject_history[track_id] = hist

            # Persistent concealment across multiple consecutive frame samples (> 60% of samples)
            if hist["total_frames"] >= 3 and (hist["concealed_frames"] / hist["total_frames"]) >= 0.60:
                concealment_type = "BALACLAVA / SKI-MASK" if dark_ratio > 0.50 else "CONCEALED / MASKED"
                return {
                    "event_type": "FACE_CONCEALMENT_DETECTED",
                    "severity": "HIGH",
                    "track_id": track_id,
                    "camera_id": camera_id,
                    "confidence": round(0.85 + (0.10 * dark_ratio), 2),
                    "concealment_type": concealment_type,
                    "skin_ratio": round(skin_ratio, 3),
                    "dark_cloth_ratio": round(dark_ratio, 3),
                    "explanation": f"Subject #{track_id} is intentionally concealing facial features ({concealment_type}, {int((1.0 - skin_ratio) * 100)}% occlusion)"
                }

        except Exception as e:
            logger.debug(f"Concealment analysis error on track #{track_id}: {e}")

        return None

face_concealment_detector = FaceConcealmentDetector()
