import time
import logging
from typing import List, Dict, Any, Optional

from app.services.ai.base import Detection
from app.services.analytics.behavior.base import (
    BaseBehaviorAnalyzer,
    BehaviorEvent,
    AnalyzerStatus
)
from app.services.analytics.behavior.analyzers import (
    LoiteringAnalyzer,
    StationaryObjectAnalyzer,
    WrongWayMovementAnalyzer,
    RestrictedAreaBehaviorAnalyzer,
    NightMovementAnalyzer,
    CrowdDensityAnalyzer,
    AbandonedObjectAnalyzer,
    RemovedObjectAnalyzer,
    RepeatedMovementAnalyzer,
    RapidMovementAnalyzer,
    SuspiciousRouteAnalyzer
)

logger = logging.getLogger("arc_vision.behavior.engine")

class BehaviorAnalyticsEngine:
    """
    Orchestrates modular behavior analysis across active tracks, zones, and tripwires.
    Operates synchronously on existing tracking telemetry without duplicate inference.
    """

    def __init__(self):
        self.analyzers: Dict[str, BaseBehaviorAnalyzer] = {
            "loitering": LoiteringAnalyzer(),
            "stationary": StationaryObjectAnalyzer(),
            "wrong_way": WrongWayMovementAnalyzer(),
            "restricted_area": RestrictedAreaBehaviorAnalyzer(),
            "night_movement": NightMovementAnalyzer(),
            "crowd_density": CrowdDensityAnalyzer(),
            "abandoned_object": AbandonedObjectAnalyzer(),
            "removed_object": RemovedObjectAnalyzer(),
            "repeated_movement": RepeatedMovementAnalyzer(),
            "rapid_movement": RapidMovementAnalyzer(),
            "suspicious_route": SuspiciousRouteAnalyzer()
        }

        # ML Behavior model slot (e.g. DeepAction / PoseAction ML)
        self.ml_model_name = "DeepAction Spatial-Temporal Action Transformer"
        self.ml_model_status = "NOT_CONFIGURED"
        self.ml_model_reason = "No neural action recognition model weights configured"

    def register_analyzer(self, key: str, analyzer: BaseBehaviorAnalyzer):
        self.analyzers[key] = analyzer

    def get_status(self) -> Dict[str, Any]:
        """Returns health telemetry for all rule-based analyzers and ML model slots."""
        analyzer_reports = {}
        for key, a in self.analyzers.items():
            analyzer_reports[key] = a.health_check()

        return {
            "engine_name": "ARC-VISION Behavior Analytics Engine (Phase H)",
            "total_analyzers": len(self.analyzers),
            "rule_analyzers_status": "READY",
            "analyzers": analyzer_reports,
            "ml_action_model": {
                "name": self.ml_model_name,
                "status": self.ml_model_status,
                "details": self.ml_model_reason
            }
        }

    def evaluate_all(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        """
        Executes all active behavior analyzers across current frame detections.
        """
        all_events: List[BehaviorEvent] = []

        for key, analyzer in self.analyzers.items():
            if analyzer.status != AnalyzerStatus.DISABLED:
                try:
                    events = analyzer.evaluate(
                        camera_id=camera_id,
                        detections=detections,
                        active_zones_by_track=active_zones_by_track,
                        tripwire_breaches_by_track=tripwire_breaches_by_track,
                        context=context
                    )
                    all_events.extend(events)
                except Exception as e:
                    logger.error(f"Error in behavior analyzer '{key}': {e}")

        return all_events

    # Backward-compatibility fallback helpers
    def evaluate_perimeter_pacing(self, detection: Detection, **kwargs) -> List[BehaviorEvent]:
        """Backward-compatible helper for perimeter pacing check."""
        analyzer = self.analyzers.get("repeated_movement")
        if analyzer:
            return analyzer.evaluate(0, [detection], {}, {})
        return []

    def evaluate_stationary_vehicle(self, detection: Detection, **kwargs) -> List[BehaviorEvent]:
        """Backward-compatible helper for stationary vehicle check."""
        analyzer = self.analyzers.get("stationary")
        if analyzer:
            return analyzer.evaluate(0, [detection], {}, {})
        return []

    def evaluate_loitering(self, detection: Detection, **kwargs) -> List[BehaviorEvent]:
        """Backward-compatible helper for loitering check."""
        analyzer = self.analyzers.get("loitering")
        if analyzer:
            return analyzer.evaluate(0, [detection], {}, {})
        return []

    def evaluate_crowd_clustering(self, detections: List[Detection], **kwargs) -> List[BehaviorEvent]:
        """Backward-compatible helper for crowd clustering check."""
        analyzer = self.analyzers.get("crowd_density")
        if analyzer:
            return analyzer.evaluate(0, detections, {}, {})
        return []

# Singleton instance
behavior_engine = BehaviorAnalyticsEngine()

