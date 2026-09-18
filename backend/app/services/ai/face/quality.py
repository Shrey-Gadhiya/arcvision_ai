import cv2
import numpy as np
from typing import Tuple, Optional, List
from app.services.ai.face.base import FaceQualityResult, FaceDetectionResult

class FaceQualityChecker:
    """
    Evaluates face image suitability for detection and biometric enrollment.
    Enforces minimum dimensions, sharpness (Laplacian variance), contrast,
    and single-face presence during enrollment.
    """

    def __init__(
        self,
        min_width: int = 40,
        min_height: int = 40,
        min_sharpness: float = 30.0,
        enroll_min_width: int = 80,
        enroll_min_height: int = 80,
        enroll_min_sharpness: float = 50.0
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.min_sharpness = min_sharpness
        self.enroll_min_width = enroll_min_width
        self.enroll_min_height = enroll_min_height
        self.enroll_min_sharpness = enroll_min_sharpness

    def compute_sharpness(self, image: np.ndarray) -> float:
        """Computes blur metric via Laplacian variance."""
        if image is None or image.size == 0:
            return 0.0
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            return float(cv2.Laplacian(gray, cv2.CV_64F).var())
        except Exception:
            return 0.0

    def compute_quality_score(self, face_crop: np.ndarray, sharpness: float) -> float:
        """
        Calculates a composite quality score (0.0 to 1.0) based on resolution,
        sharpness, and illumination.
        """
        if face_crop is None or face_crop.size == 0:
            return 0.0

        h, w = face_crop.shape[:2]
        # Resolution factor (asymptotic to 1.0 at ~200px)
        res_factor = min(1.0, (w * h) / (160.0 * 160.0))
        
        # Sharpness factor (asymptotic to 1.0 at ~200 variance)
        sharp_factor = min(1.0, sharpness / 200.0)

        # Brightness / contrast check
        if len(face_crop.shape) == 3:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_crop
        mean_b = float(np.mean(gray))
        std_b = float(np.std(gray))

        # Penalty if severely under- or over-exposed
        illum_factor = 1.0
        if mean_b < 40 or mean_b > 220:
            illum_factor = 0.5
        elif mean_b < 60 or mean_b > 200:
            illum_factor = 0.8

        if std_b < 20: # Very low contrast / washed out
            illum_factor *= 0.6

        composite = (0.4 * res_factor + 0.4 * sharp_factor + 0.2 * illum_factor)
        return float(np.clip(composite, 0.0, 1.0))

    def evaluate_face_crop(self, face_crop: np.ndarray) -> Tuple[float, float, str]:
        """Evaluates a single detected face crop for live telemetry."""
        if face_crop is None or face_crop.size == 0:
            return 0.0, 0.0, "Empty crop"

        h, w = face_crop.shape[:2]
        sharpness = self.compute_sharpness(face_crop)
        quality = self.compute_quality_score(face_crop, sharpness)

        diags = []
        if w < self.min_width or h < self.min_height:
            diags.append(f"Low resolution ({w}x{h})")
        if sharpness < self.min_sharpness:
            diags.append(f"Blurred (var={sharpness:.1f})")

        diag_str = ", ".join(diags) if diags else f"Nominal ({w}x{h}, Q={quality:.2f})"
        return quality, sharpness, diag_str

    def validate_for_enrollment(
        self,
        full_image: np.ndarray,
        detected_faces: List[FaceDetectionResult]
    ) -> FaceQualityResult:
        """
        Strict validation for enrollment:
        - Must contain exactly 1 face.
        - Face must exceed enrollment resolution and sharpness thresholds.
        """
        if full_image is None or full_image.size == 0:
            return FaceQualityResult(
                passed=False,
                quality_score=0.0,
                sharpness_score=0.0,
                face_count=0,
                diagnostics="Image is empty or corrupt",
                rejected_reason="EMPTY_IMAGE"
            )

        face_count = len(detected_faces)
        if face_count == 0:
            return FaceQualityResult(
                passed=False,
                quality_score=0.0,
                sharpness_score=0.0,
                face_count=0,
                diagnostics="No face detected in enrollment image",
                rejected_reason="NO_FACE_DETECTED"
            )

        if face_count > 1:
            return FaceQualityResult(
                passed=False,
                quality_score=0.0,
                sharpness_score=0.0,
                face_count=face_count,
                diagnostics=f"Multiple faces detected ({face_count}). Single face required for identity enrollment.",
                rejected_reason="MULTIPLE_FACES_DETECTED"
            )

        primary_face = detected_faces[0]
        crop = primary_face.face_crop
        if crop is None or crop.size == 0:
            return FaceQualityResult(
                passed=False,
                quality_score=0.0,
                sharpness_score=0.0,
                face_count=1,
                diagnostics="Failed to extract face crop",
                rejected_reason="CROP_EXTRACTION_FAILED"
            )

        h, w = crop.shape[:2]
        sharpness = self.compute_sharpness(crop)
        quality = self.compute_quality_score(crop, sharpness)

        if w < self.enroll_min_width or h < self.enroll_min_height:
            return FaceQualityResult(
                passed=False,
                quality_score=quality,
                sharpness_score=sharpness,
                face_count=1,
                diagnostics=f"Face resolution too low ({w}x{h} < {self.enroll_min_width}x{self.enroll_min_height})",
                rejected_reason="LOW_RESOLUTION"
            )

        if sharpness < self.enroll_min_sharpness:
            return FaceQualityResult(
                passed=False,
                quality_score=quality,
                sharpness_score=sharpness,
                face_count=1,
                diagnostics=f"Face is blurry or out of focus (sharpness={sharpness:.1f} < {self.enroll_min_sharpness})",
                rejected_reason="BLUR_EXCEEDED"
            )

        return FaceQualityResult(
            passed=True,
            quality_score=quality,
            sharpness_score=sharpness,
            face_count=1,
            diagnostics=f"Passed quality check (dim={w}x{h}, sharp={sharpness:.1f}, Q={quality:.2f})"
        )
