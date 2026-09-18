import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.cross_camera import CameraTopology

logger = logging.getLogger("arc_vision.cross_camera.topology")

class TopologyManager:
    """
    Manages the camera adjacency graph and validates spatial-temporal transition feasibility.
    """
    def __init__(self):
        # Cache: (from_cam, to_cam) -> dict of link attributes
        self._links: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self._default_initialized = False

    def initialize_defaults(self):
        if self._default_initialized:
            return
        # Default spatial links for standard multi-camera perimeter setup
        default_edges = [
            (1, 2, 60.0, 3.0, 45.0, "BIDIRECTIONAL", "Sector North - Perimeter Road"),
            (2, 3, 120.0, 5.0, 90.0, "BIDIRECTIONAL", "Sector North - Checkpoint Alpha"),
            (1, 3, 180.0, 8.0, 140.0, "BIDIRECTIONAL", "Sector North - Main Arterial"),
            (3, 4, 80.0, 4.0, 60.0, "BIDIRECTIONAL", "Sector East - Perimeter Gate"),
            (4, 5, 100.0, 5.0, 75.0, "BIDIRECTIONAL", "Sector South - Sterile Buffer"),
        ]
        for (u, v, dist, t_min, t_max, direct, sec) in default_edges:
            self.add_link(u, v, dist, t_min, t_max, direct, sec)
            if direct == "BIDIRECTIONAL":
                self.add_link(v, u, dist, t_min, t_max, direct, sec)
        self._default_initialized = True

    def add_link(
        self,
        from_cam: int,
        to_cam: int,
        distance_m: float = 50.0,
        min_sec: float = 2.0,
        max_sec: float = 60.0,
        direction: str = "BIDIRECTIONAL",
        sector: str = "General Sector"
    ):
        self._links[(from_cam, to_cam)] = {
            "from_camera_id": from_cam,
            "to_camera_id": to_cam,
            "distance_meters": distance_m,
            "min_travel_sec": min_sec,
            "max_travel_sec": max_sec,
            "direction": direction,
            "sector": sector,
            "is_active": True
        }

    def remove_link(self, from_cam: int, to_cam: int):
        self._links.pop((from_cam, to_cam), None)

    def is_adjacent(self, from_cam: int, to_cam: int) -> bool:
        if from_cam == to_cam:
            return True
        return (from_cam, to_cam) in self._links

    def validate_transition(
        self,
        from_cam: int,
        to_cam: int,
        delta_seconds: float
    ) -> Tuple[bool, float, Optional[Dict[str, Any]]]:
        """
        Validates if transitioning from Camera A to Camera B within delta_seconds is plausible.
        Returns: (is_plausible, transition_confidence, link_metadata)
        """
        if from_cam == to_cam:
            return True, 0.95, None

        link = self._links.get((from_cam, to_cam))
        if not link:
            # Not directly adjacent: check if time is plausible for general sector transit
            if 10.0 <= delta_seconds <= 300.0:
                return True, 0.50, None
            return False, 0.0, None

        min_t = link["min_travel_sec"]
        max_t = link["max_travel_sec"]

        if min_t <= delta_seconds <= max_t:
            # Optimal transit window
            conf = 0.88 + 0.10 * (1.0 - abs(delta_seconds - (min_t + max_t) / 2.0) / ((max_t - min_t) / 2.0 + 1e-5))
            return True, min(0.98, conf), link
        elif delta_seconds < min_t:
            # Impossibly fast transition (teleportation/different entity)
            return False, 0.10, link
        elif delta_seconds <= (max_t * 2.0):
            # Slightly delayed transit (loitering/stopping between cameras)
            return True, 0.65, link
        else:
            # Transition window expired
            return False, 0.20, link

    def get_all_links(self) -> List[Dict[str, Any]]:
        self.initialize_defaults()
        return list(self._links.values())

topology_manager = TopologyManager()
topology_manager.initialize_defaults()
