import math
import json
import time
from typing import List, Dict, Tuple, Any, Optional

def is_point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    """
    Ray-casting algorithm to test if point (x, y) is inside polygon.
    All coordinates normalized (0.0 to 1.0).
    """
    num_points = len(polygon)
    if num_points < 3:
        return False
        
    inside = False
    p1x, p1y = polygon[0]
    for i in range(num_points + 1):
        p2x, p2y = polygon[i % num_points]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def do_lines_intersect(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """
    Returns True if line segment AB and line segment CD intersect.
    """
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

def get_crossing_direction(
    p_prev: Tuple[float, float],
    p_curr: Tuple[float, float],
    line_start: Tuple[float, float],
    line_end: Tuple[float, float]
) -> str:
    """
    Determines crossing direction relative to tripwire line from start -> end.
    Returns "A_TO_B" (crossing from left to right of vector) or "B_TO_A" (right to left).
    """
    lx = line_end[0] - line_start[0]
    ly = line_end[1] - line_start[1]
    cross = lx * (p_curr[1] - p_prev[1]) - ly * (p_curr[0] - p_prev[0])
    
    if cross > 0:
        return "A_TO_B"
    elif cross < 0:
        return "B_TO_A"
    return "UNKNOWN"

class ZoneAnalyticsEngine:
    def __init__(self):
        # Per-camera line crossing counts: {cam_id: {"in": int, "out": int, "occupancy": int}}
        self._counts: Dict[int, Dict[str, int]] = {}
        self._counted_tracks: Dict[Tuple[int, int], str] = {} # (cam_id, track_id) -> direction

    def get_camera_counts(self, camera_id: int) -> Dict[str, int]:
        if camera_id not in self._counts:
            self._counts[camera_id] = {"in_count": 0, "out_count": 0, "occupancy": 0}
        return dict(self._counts[camera_id])

    def register_crossing(self, camera_id: int, track_id: int, direction: str, class_name: str = "person"):
        key = (camera_id, track_id)
        if key in self._counted_tracks:
            return
        
        counts = self.get_camera_counts(camera_id)
        if direction in ("A_TO_B", "ENTRY", "IN"):
            counts["in_count"] += 1
            counts["occupancy"] = max(0, counts["in_count"] - counts["out_count"])
            self._counted_tracks[key] = "IN"
        elif direction in ("B_TO_A", "EXIT", "OUT"):
            counts["out_count"] += 1
            counts["occupancy"] = max(0, counts["in_count"] - counts["out_count"])
            self._counted_tracks[key] = "OUT"
        self._counts[camera_id] = counts

    @staticmethod
    def point_in_polygon(point: Tuple[float, float], polygon: List[Any]) -> bool:
        if not polygon or len(polygon) < 3:
            return False
        pts = []
        for p in polygon:
            if isinstance(p, dict):
                pts.append((float(p.get("x", 0.0)), float(p.get("y", 0.0))))
            elif isinstance(p, (list, tuple)):
                pts.append((float(p[0]), float(p[1])))
        return is_point_in_polygon(point[0], point[1], pts)

    @staticmethod
    def check_zone_occupancy(centroid: Tuple[float, float], zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cx, cy = centroid
        active_in = []
        for zone in zones:
            points = zone.get("points") or zone.get("polygon") or []
            if ZoneAnalyticsEngine.point_in_polygon((cx, cy), points):
                active_in.append(zone)
        return active_in

    def check_tripwire_crossing(
        self,
        trajectory: List[Tuple[float, float, float]],
        tripwires: List[Dict[str, Any]],
        camera_id: int = 1,
        track_id: int = -1,
        class_name: str = "person"
    ) -> List[Dict[str, Any]]:
        if len(trajectory) < 2:
            return []

        p_prev = (trajectory[-2][0], trajectory[-2][1])
        p_curr = (trajectory[-1][0], trajectory[-1][1])

        breaches = []
        for tw in tripwires:
            start = tw["line"]["start"]
            end = tw["line"]["end"]

            if do_lines_intersect(p_prev, p_curr, start, end):
                direction = get_crossing_direction(p_prev, p_curr, start, end)
                required_dir = tw.get("direction", "BIDIRECTIONAL")
                
                # Update bidirectional In/Out entry counter
                self.register_crossing(camera_id, track_id, direction, class_name)

                if required_dir == "BIDIRECTIONAL" or required_dir == direction:
                    breaches.append({
                        "tripwire": tw,
                        "crossing_direction": direction
                    })

        return breaches

    @staticmethod
    def check_one_way_lane_violation(
        trajectory: List[Tuple[float, float, float]],
        lane_angle_deg: float, # Expected heading direction in degrees (0 to 360)
        tolerance_deg: float = 85.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detects if a vehicle is travelling against the authorized one-way traffic lane.
        """
        if len(trajectory) < 3:
            return None

        # Compute movement vector over last 3 points
        dx = trajectory[-1][0] - trajectory[0][0]
        dy = trajectory[-1][1] - trajectory[0][1]
        dist = math.hypot(dx, dy)
        if dist < 0.05:
            return None

        # Actual vehicle heading angle in degrees (0 = East, 90 = South, 180 = West, 270 = North)
        actual_angle = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
        angle_diff = abs(actual_angle - lane_angle_deg)
        if angle_diff > 180.0:
            angle_diff = 360.0 - angle_diff

        # If vehicle heading is opposing allowed lane angle by > tolerance (> 100 degrees = wrong way)
        if angle_diff > (180.0 - tolerance_deg):
            return {
                "is_violation": True,
                "actual_angle": round(actual_angle, 1),
                "expected_angle": round(lane_angle_deg, 1),
                "angle_diff": round(angle_diff, 1)
            }
        return None

zone_engine = ZoneAnalyticsEngine()
