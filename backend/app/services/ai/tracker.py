import math
import time
from typing import List, Dict, Tuple, Optional
import numpy as np
from app.services.ai.base import Detection

class TrackedObject:
    def __init__(self, track_id: int, detection: Detection):
        self.track_id = track_id
        self.class_name = detection.class_name
        self.confidence = detection.confidence
        self.box = detection.box  # [x1, y1, x2, y2]
        
        # Center point
        cx = (self.box[0] + self.box[2]) / 2.0
        cy = (self.box[1] + self.box[3]) / 2.0
        
        self.centroid = (cx, cy)
        self.trajectory: List[Tuple[float, float, float]] = [(cx, cy, time.time())] # x, y, timestamp
        self.velocity = (0.0, 0.0) # (dx/dt, dy/dt) in normalized units/sec
        
        self.start_time = time.time()
        self.last_seen = time.time()
        self.missed_frames = 0
        self.direction_reversals = 0 # Count direction flips for pacing detection
        self.last_heading = None
        self.total_distance = 0.0

    def update(self, detection: Detection):
        now = time.time()
        dt = max(0.001, now - self.last_seen)
        
        self.box = detection.box
        self.confidence = detection.confidence
        
        cx = (self.box[0] + self.box[2]) / 2.0
        cy = (self.box[1] + self.box[3]) / 2.0
        prev_cx, prev_cy = self.centroid
        
        dist = math.hypot(cx - prev_cx, cy - prev_cy)
        self.total_distance += dist
        
        # Velocity
        vx = (cx - prev_cx) / dt
        vy = (cy - prev_cy) / dt
        self.velocity = (vx, vy)
        
        # Check direction reversal (pacing detection)
        if dist > 0.01:
            current_heading = math.atan2(vy, vx)
            if self.last_heading is not None:
                angle_diff = abs(current_heading - self.last_heading)
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                if angle_diff > 2.0: # ~115 degrees reversal
                    self.direction_reversals += 1
            self.last_heading = current_heading

        self.centroid = (cx, cy)
        self.trajectory.append((cx, cy, now))
        if len(self.trajectory) > 60: # Retain last ~60 position samples
            self.trajectory.pop(0)
            
        self.last_seen = now
        self.missed_frames = 0

    @property
    def dwell_duration(self) -> float:
        return self.last_seen - self.start_time

    @property
    def is_stationary(self) -> bool:
        # If active for > 5 seconds but net displacement in last 5s is < 0.03
        if self.dwell_duration < 4.0:
            return False
        if len(self.trajectory) < 10:
            return False
        oldest_cx, oldest_cy, _ = self.trajectory[0]
        curr_cx, curr_cy = self.centroid
        net_disp = math.hypot(curr_cx - oldest_cx, curr_cy - oldest_cy)
        return net_disp < 0.04

    def predict(self, dt: float) -> Detection:
        """Projects bounding box and centroid forward based on velocity vector for smooth 30 FPS playback."""
        # Clamp extrapolation delta to prevent overshoot on stops
        dt_clamped = min(0.6, max(0.0, dt))
        dx = self.velocity[0] * dt_clamped
        dy = self.velocity[1] * dt_clamped
        
        dx = max(-0.06, min(0.06, dx))
        dy = max(-0.06, min(0.06, dy))

        x1 = max(0.0, min(0.98, self.box[0] + dx))
        y1 = max(0.0, min(0.98, self.box[1] + dy))
        x2 = max(x1 + 0.02, min(1.0, self.box[2] + dx))
        y2 = max(y1 + 0.02, min(1.0, self.box[3] + dy))

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        return Detection(
            class_name=self.class_name,
            confidence=self.confidence,
            box=[x1, y1, x2, y2],
            track_id=self.track_id,
            attributes={
                "centroid": (cx, cy),
                "velocity": self.velocity,
                "dwell_sec": round(self.dwell_duration, 1),
                "is_stationary": self.is_stationary,
                "pacing_count": self.direction_reversals,
                "trajectory": [(round(p[0], 3), round(p[1], 3)) for p in self.trajectory[-15:]]
            }
        )

    def to_detection(self) -> Detection:
        return Detection(
            class_name=self.class_name,
            confidence=self.confidence,
            box=self.box,
            track_id=self.track_id,
            attributes={
                "centroid": self.centroid,
                "velocity": self.velocity,
                "dwell_sec": round(self.dwell_duration, 1),
                "is_stationary": self.is_stationary,
                "pacing_count": self.direction_reversals,
                "trajectory": [(round(p[0], 3), round(p[1], 3)) for p in self.trajectory[-15:]]
            }
        )

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    # Determine coordinates of intersection rectangle
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_width = max(0.0, xB - xA)
    inter_height = max(0.0, yB - yA)
    inter_area = inter_width * inter_height

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    union_area = boxA_area + boxB_area - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area

class MultiObjectTracker:
    def __init__(self, max_missed_frames: int = 15, iou_threshold: float = 0.25):
        self.max_missed_frames = max_missed_frames
        self.iou_threshold = iou_threshold
        self.tracks: Dict[int, TrackedObject] = {}
        self._next_id = 1

    def update(self, detections: List[Detection]) -> List[Detection]:
        # Increment missed frames for existing tracks
        for track in self.tracks.values():
            track.missed_frames += 1

        matched_tracks = set()
        matched_detections = set()

        # Match existing tracks with detections based on IOU and class
        for det_idx, det in enumerate(detections):
            best_iou = 0.0
            best_track_id = None
            for track_id, track in self.tracks.items():
                if track_id in matched_tracks:
                    continue
                if track.class_name != det.class_name:
                    continue
                iou = calculate_iou(track.box, det.box)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is not None and best_iou >= self.iou_threshold:
                self.tracks[best_track_id].update(det)
                matched_tracks.add(best_track_id)
                matched_detections.add(det_idx)

        # Create new tracks for unmatched detections
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_detections:
                new_track_id = self._next_id
                self._next_id += 1
                self.tracks[new_track_id] = TrackedObject(new_track_id, det)

        # Remove stale tracks
        dead_tracks = [t_id for t_id, t in self.tracks.items() if t.missed_frames > self.max_missed_frames]
        for t_id in dead_tracks:
            del self.tracks[t_id]

        # Return active detections with assigned track_id and attributes
        result: List[Detection] = []
        for track in self.tracks.values():
            if track.missed_frames == 0:
                result.append(track.to_detection())
        return result

    def predict_all(self, dt: float) -> List[Detection]:
        """Returns forward-projected detections for intermediate frames between detector updates."""
        res: List[Detection] = []
        for track in self.tracks.values():
            if track.missed_frames <= 2:
                res.append(track.predict(dt))
        return res
