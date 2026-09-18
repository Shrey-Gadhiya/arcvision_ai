import json
from typing import List, Dict, Tuple, Any

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
    # Vector of the tripwire: L = line_end - line_start
    lx = line_end[0] - line_start[0]
    ly = line_end[1] - line_start[1]
    
    # Vector of movement: M = p_curr - p_prev
    # 2D Cross product: L.x * M.y - L.y * M.x
    cross = lx * (p_curr[1] - p_prev[1]) - ly * (p_curr[0] - p_prev[0])
    
    if cross > 0:
        return "A_TO_B"
    elif cross < 0:
        return "B_TO_A"
    return "UNKNOWN"

class ZoneAnalyticsEngine:
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
        """
        Tests centroid (x, y) against all active zones.
        """
        cx, cy = centroid
        active_in = []
        for zone in zones:
            points = zone.get("points") or zone.get("polygon") or []
            if ZoneAnalyticsEngine.point_in_polygon((cx, cy), points):
                active_in.append(zone)
        return active_in

    @staticmethod
    def check_tripwire_crossing(
        trajectory: List[Tuple[float, float, float]],
        tripwires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Tests if the last trajectory segment crossed any active tripwires.
        """
        if len(trajectory) < 2:
            return []

        p_prev = (trajectory[-2][0], trajectory[-2][1])
        p_curr = (trajectory[-1][0], trajectory[-1][1])

        breaches = []
        for tw in tripwires:
            start = tw["line"]["start"] # (x, y)
            end = tw["line"]["end"]     # (x, y)

            if do_lines_intersect(p_prev, p_curr, start, end):
                direction = get_crossing_direction(p_prev, p_curr, start, end)
                required_dir = tw.get("direction", "BIDIRECTIONAL")
                if required_dir == "BIDIRECTIONAL" or required_dir == direction:
                    breaches.append({
                        "tripwire": tw,
                        "crossing_direction": direction
                    })

        return breaches

zone_engine = ZoneAnalyticsEngine()
