import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from app.services.ai.perception.base import BaseModelAdapter, PerceptionTask, ModelStatus

logger = logging.getLogger("arc_vision.perception.crowd")

class CrowdAnalyzer(BaseModelAdapter):
    """
    Real-time spatial crowd intelligence engine.
    Calculates zone density, head counts, spatial growth rate, and persistence windows.
    """
    def __init__(
        self,
        name: str = "Crowd Intelligence & Spatial Density Engine",
        version: str = "2.0.0",
        default_density_threshold: int = 8,
        persistence_sec: float = 5.0
    ):
        super().__init__(
            name=name,
            version=version,
            task=PerceptionTask.CROWD_ANALYSIS,
            provider="ARC-VISION Spatial Analytics",
            model_path="app/services/ai/perception/crowd_analyzer.py",
            device="CPU",
            input_resolution="Multi-Track Spatial Coordinates",
            supported_classes=["crowd_formation", "density_threshold_breach", "rapid_surge"]
        )
        self.default_density_threshold = default_density_threshold
        self.persistence_sec = persistence_sec
        
        # State: (camera_id, zone_id) -> {"count": int, "first_exceeded": float, "last_fired": float, "history": List[Tuple[float, int]]}
        self._zone_states: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.status = ModelStatus.ACTIVE
        self.is_loaded = True
        self.memory_mb = 5.0

    def load(self) -> bool:
        self.status = ModelStatus.ACTIVE
        self.is_loaded = True
        return True

    def unload(self) -> bool:
        self._zone_states.clear()
        self.status = ModelStatus.STANDBY
        self.is_loaded = False
        return True

    def analyze_crowd(
        self,
        camera_id: int,
        tracked_persons: List[Any],
        zones: List[Dict[str, Any]],
        threshold: Optional[int] = None,
        current_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluates crowd density per zone, calculates growth rate and triggers events upon persistent threshold breach.
        """
        now = current_time or time.time()
        start_t = time.time()
        thresh = threshold or self.default_density_threshold
        events: List[Dict[str, Any]] = []

        from app.services.analytics.zone_engine import zone_engine

        # Map person centroids
        centroids = [det.attributes.get("centroid", (0.5, 0.5)) for det in tracked_persons if det.class_name == "person"]

        for zone in zones:
            zone_id = zone.get("id", 0)
            poly = zone.get("polygon", [])
            if not poly or len(poly) < 3:
                continue

            # Count people in this specific zone polygon
            in_zone_count = sum(1 for c in centroids if zone_engine.point_in_polygon(c, poly))

            state_key = (camera_id, zone_id)
            if state_key not in self._zone_states:
                self._zone_states[state_key] = {
                    "count": in_zone_count,
                    "first_exceeded": 0.0,
                    "last_fired": -999.0,
                    "history": [(now, in_zone_count)]
                }

            state = self._zone_states[state_key]
            state["count"] = in_zone_count
            state["history"].append((now, in_zone_count))
            # Keep 30s history
            state["history"] = [(t, c) for (t, c) in state["history"] if (now - t) <= 30.0]

            # Compute growth rate (people / minute)
            growth_rate = 0.0
            if len(state["history"]) >= 2:
                dt = state["history"][-1][0] - state["history"][0][0]
                if dt > 2.0:
                    dc = state["history"][-1][1] - state["history"][0][1]
                    growth_rate = round((dc / dt) * 60.0, 1)

            if in_zone_count >= thresh:
                if state["first_exceeded"] == 0.0:
                    state["first_exceeded"] = now

                duration = now - state["first_exceeded"]
                if duration >= self.persistence_sec and (now - state["last_fired"]) > 45.0:
                    state["last_fired"] = now
                    events.append({
                        "event_type": "CROWD_DENSITY_THRESHOLD",
                        "camera_id": camera_id,
                        "zone_id": zone_id,
                        "zone_name": zone.get("name", f"Zone #{zone_id}"),
                        "count": in_zone_count,
                        "threshold": thresh,
                        "growth_rate_per_min": growth_rate,
                        "duration_sec": round(duration, 1),
                        "severity": "HIGH" if in_zone_count >= (thresh * 1.5) else "MEDIUM",
                        "explanation": f"Crowd density threshold exceeded in {zone.get('name')}: {in_zone_count} people (Threshold: {thresh}, Growth: {growth_rate:+.1f}/min)"
                    })
            else:
                state["first_exceeded"] = 0.0

        latency = (time.time() - start_t) * 1000.0
        self.record_inference(latency)
        return events
