import math
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import enum
import numpy as np

from app.services.ai.base import Detection
from app.models.rule import RuleSeverity, RuleEventType

class AnalyzerStatus(str, enum.Enum):
    READY = "READY"
    STANDBY = "STANDBY"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DISABLED = "DISABLED"

@dataclass
class BehaviorEvent:
    event_type: str
    camera_id: int
    track_id: int
    class_name: str
    severity: str = "HIGH"
    confidence: float = 0.85
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    tripwire_id: Optional[int] = None
    tripwire_name: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "class_name": self.class_name,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "tripwire_id": self.tripwire_id,
            "tripwire_name": self.tripwire_name,
            "details": self.details,
            "timestamp": self.timestamp
        }

class BehaviorFeatureExtractor:
    """
    Extracts trajectory kinematics, displacement vectors, velocity,
    heading, direction reversals, and spatial occupancy features.
    """

    @staticmethod
    def compute_displacement(trajectory: List[Tuple[float, float, float]]) -> float:
        """Net Euclidean displacement between oldest and newest trajectory points (normalized 0.0 to 1.414)."""
        if not trajectory or len(trajectory) < 2:
            return 0.0
        x0, y0 = trajectory[0][0], trajectory[0][1]
        x1, y1 = trajectory[-1][0], trajectory[-1][1]
        return float(math.hypot(x1 - x0, y1 - y0))

    @staticmethod
    def compute_cumulative_distance(trajectory: List[Tuple[float, float, float]]) -> float:
        """Total path length along the trajectory history."""
        if not trajectory or len(trajectory) < 2:
            return 0.0
        total = 0.0
        for i in range(1, len(trajectory)):
            dx = trajectory[i][0] - trajectory[i-1][0]
            dy = trajectory[i][1] - trajectory[i-1][1]
            total += math.hypot(dx, dy)
        return float(total)

    @staticmethod
    def compute_speed(trajectory: List[Tuple[float, float, float]]) -> float:
        """Velocity in normalized frame units per second."""
        if not trajectory or len(trajectory) < 2:
            return 0.0
        # Average over recent ~5-10 samples
        recent = trajectory[-10:]
        t_delta = max(0.01, recent[-1][2] - recent[0][2])
        dist = 0.0
        for i in range(1, len(recent)):
            dist += math.hypot(recent[i][0] - recent[i-1][0], recent[i][1] - recent[i-1][1])
        return float(dist / t_delta)

    @staticmethod
    def compute_heading_vector(trajectory: List[Tuple[float, float, float]]) -> Tuple[float, float]:
        """Calculates normalized unit heading vector (dx, dy). Returns (0.0, 0.0) if stationary."""
        if not trajectory or len(trajectory) < 2:
            return (0.0, 0.0)
        recent = trajectory[-8:]
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        mag = math.hypot(dx, dy)
        if mag < 0.005:
            return (0.0, 0.0)
        return (dx / mag, dy / mag)

    @staticmethod
    def compute_heading_angle(trajectory: List[Tuple[float, float, float]]) -> Optional[float]:
        """Calculates direction in radians [-pi, pi]."""
        vx, vy = BehaviorFeatureExtractor.compute_heading_vector(trajectory)
        if vx == 0.0 and vy == 0.0:
            return None
        return math.atan2(vy, vx)

    @staticmethod
    def compute_direction_reversals(trajectory: List[Tuple[float, float, float]], threshold_rad: float = 2.0) -> int:
        """Counts sharp heading reversals (> ~115 degrees) for pacing detection."""
        if not trajectory or len(trajectory) < 3:
            return 0
        reversals = 0
        last_angle = None
        for i in range(1, len(trajectory)):
            dx = trajectory[i][0] - trajectory[i-1][0]
            dy = trajectory[i][1] - trajectory[i-1][1]
            if math.hypot(dx, dy) < 0.01:
                continue
            angle = math.atan2(dy, dx)
            if last_angle is not None:
                diff = abs(angle - last_angle)
                if diff > math.pi:
                    diff = 2 * math.pi - diff
                if diff >= threshold_rad:
                    reversals += 1
            last_angle = angle
        return reversals

class BaseBehaviorAnalyzer(ABC):
    """
    Abstract contract for modular behavior analysis engines.
    """
    def __init__(self, name: str, event_type: str):
        self.name = name
        self.event_type = event_type
        self.status = AnalyzerStatus.READY
        self.total_evaluations: int = 0
        self.total_events_generated: int = 0

    @abstractmethod
    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        """Evaluates track telemetry against behavioral criteria."""
        pass

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "event_type": self.event_type,
            "status": self.status.value,
            "total_evaluations": self.total_evaluations,
            "total_events_generated": self.total_events_generated
        }
