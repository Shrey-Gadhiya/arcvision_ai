import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

class MotionDetector:
    """
    Frigate-class pre-inference motion detection layer.
    Filters frames before expensive deep-learning object inference to conserve GPU/CPU resources.
    """
    def __init__(
        self,
        threshold: int = 25,
        min_area: int = 500,
        detect_resolution: Tuple[int, int] = (640, 360)
    ):
        self.threshold = threshold
        self.min_area = min_area
        self.detect_w, self.detect_h = detect_resolution
        
        # MOG2 background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300,
            varThreshold=self.threshold,
            detectShadows=False
        )
        self.frame_count = 0

    def update_params(self, threshold: Optional[int] = None, min_area: Optional[int] = None):
        if threshold is not None:
            self.threshold = threshold
            self.bg_subtractor.setVarThreshold(self.threshold)
        if min_area is not None:
            self.min_area = min_area

    def detect(
        self,
        frame: np.ndarray,
        motion_masks: Optional[List[List[Tuple[float, float]]]] = None
    ) -> Tuple[bool, float, List[List[float]], np.ndarray]:
        """
        Analyzes frame for motion.
        
        Args:
            frame: Full BGR video frame
            motion_masks: List of normalized polygon coordinates to mask out [[(x, y), ...]]
            
        Returns:
            has_motion: bool
            motion_score: float (0.0 to 1.0)
            motion_boxes: List of normalized [x1, y1, x2, y2] bounding boxes
            fg_mask: Foreground binary motion mask
        """
        self.frame_count += 1
        orig_h, orig_w = frame.shape[:2]
        
        # 1. Downscale to detect resolution for fast processing (< 2ms)
        small_frame = cv2.resize(frame, (self.detect_w, self.detect_h))
        blurred = cv2.GaussianBlur(small_frame, (5, 5), 0)

        # 2. Compute foreground mask using MOG2
        fg_mask = self.bg_subtractor.apply(blurred)

        # 3. Apply motion masks (ignore irrelevant zones like swaying trees or flags)
        if motion_masks:
            for mask_pts in motion_masks:
                if len(mask_pts) >= 3:
                    pts = np.array([
                        [int(p[0] * self.detect_w), int(p[1] * self.detect_h)]
                        for p in mask_pts
                    ], np.int32)
                    cv2.fillPoly(fg_mask, [pts], 0) # Black out masked areas

        # 4. Clean noise with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cleaned_mask = cv2.dilate(cleaned_mask, kernel, iterations=2)

        # 5. Extract contours
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_boxes: List[List[float]] = []
        total_motion_pixels = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                total_motion_pixels += area
                # Normalize box [x1, y1, x2, y2]
                norm_box = [
                    x / float(self.detect_w),
                    y / float(self.detect_h),
                    (x + w) / float(self.detect_w),
                    (y + h) / float(self.detect_h)
                ]
                motion_boxes.append(norm_box)

        total_pixels = self.detect_w * self.detect_h
        motion_score = min(1.0, float(total_motion_pixels) / float(total_pixels * 0.25))
        has_motion = len(motion_boxes) > 0

        return has_motion, motion_score, motion_boxes, cleaned_mask
