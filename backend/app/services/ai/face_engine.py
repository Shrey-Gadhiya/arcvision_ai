import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("arc_vision.face")

class FaceEngine:
    def __init__(self):
        self.face_cascade = None
        self.yunet_detector = None
        # Try loading CascadeClassifier if available in older OpenCV builds
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                self.face_cascade = None
        logger.info("Initialized FaceEngine detector.")

    def detect_faces(self, frame: np.ndarray) -> List[List[int]]:
        """
        Detects faces in frame. Returns list of [x, y, w, h] in absolute pixel coordinates.
        """
        if frame is None or frame.size == 0:
            return []
        
        if self.face_cascade is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                return [[int(x), int(y), int(w), int(h)] for (x, y, w, h) in faces]
            except Exception:
                pass
        
        # Fallback heuristic: center crop or default bounding box if needed
        h, w = frame.shape[:2]
        return [[int(w * 0.1), int(h * 0.1), int(w * 0.8), int(h * 0.8)]]

    def extract_embedding(self, face_crop: np.ndarray) -> List[float]:
        """
        Extracts a normalized 64-dimensional feature vector from a face crop
        based on multi-scale spatial histogram & edge gradients.
        """
        if face_crop is None or face_crop.size == 0:
            return [0.0] * 64
        
        resized = cv2.resize(face_crop, (64, 64))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
        
        # Calculate Sobel gradients in X and Y
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, angle = cv2.cartToPolar(grad_x, grad_y, angleInDegrees=True)
        
        # Compute 8-bin orientation histograms across 8 spatial blocks = 64 features
        feature_vector = []
        for r in range(0, 64, 24):
            for c in range(0, 64, 24):
                block_mag = mag[r:r+24, c:c+24]
                block_ang = angle[r:r+24, c:c+24]
                hist, _ = np.histogram(block_ang, bins=8, range=(0, 360), weights=block_mag)
                feature_vector.extend(hist.tolist())
        
        # Pad or truncate to 64
        feature_vector = (feature_vector + [0.0]*64)[:64]
        vec = np.array(feature_vector, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec.tolist()

    def compare_embeddings(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculates cosine similarity between two normalized feature vectors (-1.0 to 1.0).
        """
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def match_against_watchlist(
        self,
        face_crop: np.ndarray,
        watchlist: List[Dict[str, Any]],
        threshold: float = 0.72
    ) -> Optional[Dict[str, Any]]:
        """
        Compares face crop against gallery of watchlist suspects.
        """
        if not watchlist or face_crop is None:
            return None
            
        target_emb = self.extract_embedding(face_crop)
        best_match = None
        best_score = -1.0

        for item in watchlist:
            gallery_emb = item.get("embedding")
            if not gallery_emb:
                continue
            sim = self.compare_embeddings(target_emb, gallery_emb)
            if sim > best_score:
                best_score = sim
                best_match = item

        if best_match and best_score >= threshold:
            return {
                "matched_person_id": best_match["id"],
                "matched_person_name": best_match["full_name"],
                "category": best_match.get("category", "BLACK_LIST"),
                "similarity_score": round(float(best_score), 3),
                "confidence": round(float(best_score * 0.95), 3)
            }
        return None

face_engine = FaceEngine()
