import cv2
import numpy as np

class NightVisionProcessor:
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        self.prev_gray = None

    def enhance_low_light(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhances low-light / night surveillance frames using Lab color space and CLAHE.
        """
        if frame is None or frame.size == 0:
            return frame

        # Convert BGR to Lab color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L-channel
        l_enhanced = self.clahe.apply(l)

        # Merge back
        enhanced_lab = cv2.merge((l_enhanced, a, b))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        return enhanced_bgr

    def convert_to_pseudo_thermal(self, frame: np.ndarray) -> np.ndarray:
        """
        Applies a military thermal color map (Ironbow / Inferno) to visualize heat signatures.
        """
        if frame is None or frame.size == 0:
            return frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        enhanced_gray = self.clahe.apply(gray)
        thermal = cv2.applyColorMap(enhanced_gray, cv2.COLORMAP_INFERNO)
        return thermal

    def detect_night_motion(self, frame: np.ndarray, min_area: int = 400) -> float:
        """
        Calculates frame-to-frame optical motion intensity.
        Returns motion ratio (0.0 to 1.0).
        """
        if frame is None or frame.size == 0:
            return 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray_blurred
            return 0.0

        frame_delta = cv2.absdiff(self.prev_gray, gray_blurred)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_motion_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > min_area)
        
        self.prev_gray = gray_blurred
        h, w = frame.shape[:2]
        motion_ratio = min(1.0, total_motion_area / (h * w))
        return motion_ratio

night_vision_processor = NightVisionProcessor()
