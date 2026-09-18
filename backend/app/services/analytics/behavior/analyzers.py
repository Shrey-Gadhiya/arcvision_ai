import math
import time
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.services.ai.base import Detection
from app.services.analytics.behavior.base import (
    BaseBehaviorAnalyzer,
    BehaviorEvent,
    BehaviorFeatureExtractor,
    AnalyzerStatus
)
from app.models.rule import RuleEventType, RuleSeverity

logger = logging.getLogger("arc_vision.behavior.analyzers")

# =========================================================================
# 1. LOITERING ANALYZER
# =========================================================================
class LoiteringAnalyzer(BaseBehaviorAnalyzer):
    """
    Flags when an entity dwells in a zone or region past a threshold while
    remaining within a confined spatial radius (low net displacement).
    """
    def __init__(self, default_dwell_sec: float = 15.0, max_radius: float = 0.18):
        super().__init__(name="LoiteringAnalyzer", event_type=RuleEventType.LOITERING.value)
        self.default_dwell_sec = default_dwell_sec
        self.max_radius = max_radius

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        for det in detections:
            dwell = det.attributes.get("dwell_sec", 0.0)
            traj = det.attributes.get("trajectory", [])
            disp = BehaviorFeatureExtractor.compute_displacement(traj) if len(traj) >= 2 and len(traj[0]) == 3 else 0.0

            zones = active_zones_by_track.get(det.track_id, [])
            for zone in zones:
                threshold = zone.get("loitering_time_sec", self.default_dwell_sec)
                if dwell >= threshold and disp <= self.max_radius:
                    ev = BehaviorEvent(
                        event_type=self.event_type,
                        camera_id=camera_id,
                        track_id=det.track_id,
                        class_name=det.class_name,
                        severity=RuleSeverity.MEDIUM.value,
                        confidence=0.88,
                        zone_id=zone.get("id"),
                        zone_name=zone.get("name"),
                        details={
                            "dwell_sec": dwell,
                            "threshold_sec": threshold,
                            "displacement": round(disp, 3),
                            "summary": f"{det.class_name.capitalize()} #{det.track_id} loitering in {zone.get('name')} for {dwell:.1f}s"
                        }
                    )
                    events.append(ev)
                    self.total_events_generated += 1

        return events


# =========================================================================
# 2. STATIONARY VEHICLE / OBJECT ANALYZER
# =========================================================================
class StationaryObjectAnalyzer(BaseBehaviorAnalyzer):
    """
    Flags vehicles or dropped objects that remain stationary beyond dwell limits.
    """
    VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "vehicle"}
    ITEM_CLASSES = {"backpack", "suitcase", "handbag", "package", "box", "chair"}

    def __init__(self, vehicle_dwell_thresh: float = 12.0, object_dwell_thresh: float = 10.0):
        super().__init__(name="StationaryObjectAnalyzer", event_type=RuleEventType.STATIONARY_OBJECT.value)
        self.vehicle_dwell_thresh = vehicle_dwell_thresh
        self.object_dwell_thresh = object_dwell_thresh

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        for det in detections:
            is_stat = det.attributes.get("is_stationary", False)
            dwell = det.attributes.get("dwell_sec", 0.0)

            cname = det.class_name.lower()
            if cname in self.VEHICLE_CLASSES and (is_stat or dwell >= self.vehicle_dwell_thresh):
                ev = BehaviorEvent(
                    event_type=RuleEventType.STATIONARY_VEHICLE.value,
                    camera_id=camera_id,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    severity=RuleSeverity.MEDIUM.value,
                    confidence=0.90,
                    details={
                        "dwell_sec": dwell,
                        "is_stationary": True,
                        "summary": f"Stationary vehicle ({det.class_name} #{det.track_id}) stopped for {dwell:.1f}s"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

            elif cname in self.ITEM_CLASSES and dwell >= self.object_dwell_thresh:
                ev = BehaviorEvent(
                    event_type=RuleEventType.STATIONARY_OBJECT.value,
                    camera_id=camera_id,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    severity=RuleSeverity.MEDIUM.value,
                    confidence=0.85,
                    details={
                        "dwell_sec": dwell,
                        "is_stationary": True,
                        "summary": f"Stationary object ({det.class_name} #{det.track_id}) stationary for {dwell:.1f}s"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events


# =========================================================================
# 3. WRONG-WAY MOVEMENT ANALYZER
# =========================================================================
class WrongWayMovementAnalyzer(BaseBehaviorAnalyzer):
    """
    Evaluates trajectory heading against allowed tripwire crossing direction
    or configured zone transit vectors.
    """
    def __init__(self):
        super().__init__(name="WrongWayMovementAnalyzer", event_type=RuleEventType.WRONG_WAY.value)

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        for det in detections:
            breaches = tripwire_breaches_by_track.get(det.track_id, [])
            for breach in breaches:
                tw = breach.get("tripwire", {})
                req_dir = tw.get("direction", "BIDIRECTIONAL")
                actual_dir = breach.get("crossing_direction")

                # If tripwire specifies strict direction and crossing violates it
                is_wrong_way = False
                if req_dir == "A_TO_B" and actual_dir == "B_TO_A":
                    is_wrong_way = True
                elif req_dir == "B_TO_A" and actual_dir == "A_TO_B":
                    is_wrong_way = True

                if is_wrong_way:
                    ev = BehaviorEvent(
                        event_type=self.event_type,
                        camera_id=camera_id,
                        track_id=det.track_id,
                        class_name=det.class_name,
                        severity=RuleSeverity.HIGH.value,
                        confidence=0.92,
                        tripwire_id=tw.get("id"),
                        tripwire_name=tw.get("name"),
                        details={
                            "expected_direction": req_dir,
                            "actual_direction": actual_dir,
                            "summary": f"{det.class_name.capitalize()} #{det.track_id} crossed {tw.get('name')} in reverse direction ({actual_dir} vs expected {req_dir})"
                        }
                    )
                    events.append(ev)
                    self.total_events_generated += 1

        return events


# =========================================================================
# 4. RESTRICTED-AREA BEHAVIOR ANALYZER
# =========================================================================
class RestrictedAreaBehaviorAnalyzer(BaseBehaviorAnalyzer):
    """
    Evaluates unauthorized presence or prohibited object classes in RESTRICTED zones.
    """
    def __init__(self):
        super().__init__(name="RestrictedAreaBehaviorAnalyzer", event_type=RuleEventType.RESTRICTED_ZONE_ACTIVITY.value)

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        for det in detections:
            zones = active_zones_by_track.get(det.track_id, [])
            for zone in zones:
                if zone.get("zone_type") in ("RESTRICTED", "EXCLUSION"):
                    dwell = det.attributes.get("dwell_sec", 0.0)
                    ev = BehaviorEvent(
                        event_type=self.event_type,
                        camera_id=camera_id,
                        track_id=det.track_id,
                        class_name=det.class_name,
                        severity=RuleSeverity.CRITICAL.value,
                        confidence=0.95,
                        zone_id=zone.get("id"),
                        zone_name=zone.get("name"),
                        details={
                            "zone_type": zone.get("zone_type"),
                            "dwell_sec": dwell,
                            "summary": f"Unauthorized {det.class_name} #{det.track_id} active in restricted zone '{zone.get('name')}'"
                        }
                    )
                    events.append(ev)
                    self.total_events_generated += 1

        return events


# =========================================================================
# 5. NIGHT-TIME MOVEMENT ANALYZER
# =========================================================================
class NightMovementAnalyzer(BaseBehaviorAnalyzer):
    """
    Combines configured night schedules (e.g. 20:00 to 06:00) with spatial occupancy.
    """
    def __init__(self, default_start_hour: int = 20, default_end_hour: int = 6):
        super().__init__(name="NightMovementAnalyzer", event_type=RuleEventType.NIGHT_MOVEMENT.value)
        self.default_start_hour = default_start_hour
        self.default_end_hour = default_end_hour

    def is_night_time(self, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and "is_night_mode" in context:
            return bool(context["is_night_mode"])
        # Check current hour
        cur_hour = time.localtime().tm_hour
        return cur_hour >= self.default_start_hour or cur_hour < self.default_end_hour

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        if not self.is_night_time(context):
            return events

        for det in detections:
            if det.confidence >= 0.40:
                zones = active_zones_by_track.get(det.track_id, [])
                z_name = zones[0].get("name") if zones else "Monitored Sector"
                ev = BehaviorEvent(
                    event_type=self.event_type,
                    camera_id=camera_id,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    severity=RuleSeverity.HIGH.value if zones else RuleSeverity.MEDIUM.value,
                    confidence=det.confidence,
                    zone_id=zones[0].get("id") if zones else None,
                    zone_name=z_name,
                    details={
                        "condition": "Night-time schedule active",
                        "summary": f"Night-time movement detected: {det.class_name} #{det.track_id} in {z_name}"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events


# =========================================================================
# 6. CROWD / DENSITY ANALYZER
# =========================================================================
class CrowdDensityAnalyzer(BaseBehaviorAnalyzer):
    """
    Monitors people count per zone and aggregates spatial clustering.
    """
    def __init__(self, crowd_threshold: int = 4):
        super().__init__(name="CrowdDensityAnalyzer", event_type=RuleEventType.CROWD_DENSITY.value)
        self.crowd_threshold = crowd_threshold

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        # Count persons per zone
        zone_counts: Dict[int, Dict[str, Any]] = {}
        total_persons = 0

        for det in detections:
            if det.class_name.lower() != "person":
                continue
            total_persons += 1
            zones = active_zones_by_track.get(det.track_id, [])
            for z in zones:
                zid = z.get("id", 0)
                if zid not in zone_counts:
                    zone_counts[zid] = {"name": z.get("name"), "count": 0, "tracks": []}
                zone_counts[zid]["count"] += 1
                zone_counts[zid]["tracks"].append(det.track_id)

        # Check zone-level thresholds
        for zid, zinfo in zone_counts.items():
            if zinfo["count"] >= self.crowd_threshold:
                ev = BehaviorEvent(
                    event_type=self.event_type,
                    camera_id=camera_id,
                    track_id=zinfo["tracks"][0] if zinfo["tracks"] else 0,
                    class_name="person_crowd",
                    severity=RuleSeverity.HIGH.value,
                    confidence=0.90,
                    zone_id=zid,
                    zone_name=zinfo["name"],
                    details={
                        "people_count": zinfo["count"],
                        "threshold": self.crowd_threshold,
                        "track_ids": zinfo["tracks"],
                        "summary": f"Crowd density threshold exceeded in {zinfo['name']}: {zinfo['count']} persons present"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events


# =========================================================================
# 7. ABANDONED OBJECT ANALYZER
# =========================================================================
class AbandonedObjectAnalyzer(BaseBehaviorAnalyzer):
    """
    Detects dropped luggage/backpacks where associated owner departs beyond
    distance threshold and object persists stationary.
    """
    LUGGAGE_CLASSES = {"backpack", "suitcase", "handbag", "package", "box"}

    def __init__(self, min_abandoned_sec: float = 12.0, separation_dist: float = 0.25):
        super().__init__(name="AbandonedObjectAnalyzer", event_type=RuleEventType.ABANDONED_OBJECT.value)
        self.min_abandoned_sec = min_abandoned_sec
        self.separation_dist = separation_dist
        # Memory of object spawn -> closest person track: {track_id: {"spawn_ts": float, "initial_owner": int, "box": list}}
        self._object_registry: Dict[int, Dict[str, Any]] = {}

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []
        now = time.time()

        persons = [d for d in detections if d.class_name.lower() == "person"]
        objects = [d for d in detections if d.class_name.lower() in self.LUGGAGE_CLASSES]

        for obj in objects:
            dwell = obj.attributes.get("dwell_sec", 0.0)
            cx, cy = obj.attributes.get("centroid", ((obj.box[0]+obj.box[2])/2, (obj.box[1]+obj.box[3])/2))

            # Register if not tracked
            if obj.track_id not in self._object_registry:
                # Find closest person
                closest_p = None
                min_d = 999.0
                for p in persons:
                    pcx, pcy = p.attributes.get("centroid", ((p.box[0]+p.box[2])/2, (p.box[1]+p.box[3])/2))
                    d = math.hypot(cx - pcx, cy - pcy)
                    if d < min_d:
                        min_d = d
                        closest_p = p.track_id

                self._object_registry[obj.track_id] = {
                    "spawn_ts": now,
                    "initial_owner": closest_p,
                    "last_cx": cx,
                    "last_cy": cy
                }

            # Check if all people have moved far away
            min_dist_to_any_person = 999.0
            for p in persons:
                pcx, pcy = p.attributes.get("centroid", ((p.box[0]+p.box[2])/2, (p.box[1]+p.box[3])/2))
                d = math.hypot(cx - pcx, cy - pcy)
                if d < min_dist_to_any_person:
                    min_dist_to_any_person = d

            # If stationary for dwell threshold and nearest person is farther than separation_dist
            if dwell >= self.min_abandoned_sec and min_dist_to_any_person >= self.separation_dist:
                ev = BehaviorEvent(
                    event_type=self.event_type,
                    camera_id=camera_id,
                    track_id=obj.track_id,
                    class_name=obj.class_name,
                    severity=RuleSeverity.HIGH.value,
                    confidence=0.88,
                    details={
                        "dwell_sec": dwell,
                        "nearest_person_dist": round(min_dist_to_any_person, 3),
                        "summary": f"Unattended/Abandoned {obj.class_name} #{obj.track_id} stationary for {dwell:.1f}s (No person within {self.separation_dist} radius)"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events


# =========================================================================
# 8. REMOVED OBJECT ANALYZER
# =========================================================================
class RemovedObjectAnalyzer(BaseBehaviorAnalyzer):
    """
    Monitors previously stationary items. Flags when an object disappears and absence persists.
    """
    def __init__(self, persistence_sec: float = 4.0):
        super().__init__(name="RemovedObjectAnalyzer", event_type=RuleEventType.REMOVED_OBJECT.value)
        self.persistence_sec = persistence_sec
        # Memory of stationary items: track_id -> {"last_seen": float, "box": list, "class": str, "reported": bool}
        self._stationary_items: Dict[int, Dict[str, Any]] = {}

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []
        now = time.time()
        active_ids = {d.track_id for d in detections}

        # Update currently seen stationary objects
        for det in detections:
            dwell = det.attributes.get("dwell_sec", 0.0)
            if dwell >= 10.0 and det.class_name.lower() in ("backpack", "suitcase", "box", "package", "equipment"):
                self._stationary_items[det.track_id] = {
                    "last_seen": now,
                    "box": det.box,
                    "class": det.class_name,
                    "reported": False
                }

        # Check vanished items
        for t_id, meta in list(self._stationary_items.items()):
            if t_id not in active_ids:
                absence = now - meta["last_seen"]
                if absence >= self.persistence_sec and not meta["reported"]:
                    meta["reported"] = True
                    ev = BehaviorEvent(
                        event_type=self.event_type,
                        camera_id=camera_id,
                        track_id=t_id,
                        class_name=meta["class"],
                        severity=RuleSeverity.HIGH.value,
                        confidence=0.85,
                        details={
                            "absence_sec": round(absence, 1),
                            "last_known_box": meta["box"],
                            "summary": f"Asset/Object removal alert: {meta['class']} #{t_id} vanished from monitored location"
                        }
                    )
                    events.append(ev)
                    self.total_events_generated += 1

        return events


# =========================================================================
# 9. REPEATED MOVEMENT (PACING) ANALYZER
# =========================================================================
class RepeatedMovementAnalyzer(BaseBehaviorAnalyzer):
    """
    Detects repeated back-and-forth pacing near perimeters.
    """
    def __init__(self, min_reversals: int = 3, min_dwell: float = 8.0):
        super().__init__(name="RepeatedMovementAnalyzer", event_type=RuleEventType.REPEATED_MOVEMENT.value)
        self.min_reversals = min_reversals
        self.min_dwell = min_dwell

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        for det in detections:
            pacing_count = det.attributes.get("pacing_count", 0)
            dwell = det.attributes.get("dwell_sec", 0.0)

            if pacing_count >= self.min_reversals and dwell >= self.min_dwell:
                zones = active_zones_by_track.get(det.track_id, [])
                z_name = zones[0].get("name") if zones else "Perimeter Area"
                ev = BehaviorEvent(
                    event_type=self.event_type,
                    camera_id=camera_id,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    severity=RuleSeverity.HIGH.value,
                    confidence=0.88,
                    zone_name=z_name,
                    details={
                        "reversals_count": pacing_count,
                        "dwell_sec": dwell,
                        "summary": f"Repeated movement / pacing pattern: {det.class_name} #{det.track_id} exhibited {pacing_count} direction reversals near {z_name}"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events


# =========================================================================
# 10. RAPID MOVEMENT ANALYZER
# =========================================================================
class RapidMovementAnalyzer(BaseBehaviorAnalyzer):
    """
    Flags velocity spikes or running behavior (speed threshold exceeded).
    """
    def __init__(self, speed_threshold: float = 0.35):
        super().__init__(name="RapidMovementAnalyzer", event_type=RuleEventType.RAPID_MOVEMENT.value)
        self.speed_threshold = speed_threshold

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []

        for det in detections:
            vx, vy = det.attributes.get("velocity", (0.0, 0.0))
            speed = math.hypot(vx, vy)

            if speed >= self.speed_threshold:
                ev = BehaviorEvent(
                    event_type=self.event_type,
                    camera_id=camera_id,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    severity=RuleSeverity.HIGH.value,
                    confidence=0.85,
                    details={
                        "speed_units_sec": round(speed, 3),
                        "speed_threshold": self.speed_threshold,
                        "summary": f"Rapid movement detected: {det.class_name} #{det.track_id} moving at high velocity ({speed:.2f} units/s)"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events


# =========================================================================
# 11. SUSPICIOUS ROUTE ANALYZER
# =========================================================================
class SuspiciousRouteAnalyzer(BaseBehaviorAnalyzer):
    """
    Matches chronological zone transit sequences (e.g. Zone A -> Zone B -> Restricted Zone)
    within a configured time window.
    """
    def __init__(self):
        super().__init__(name="SuspiciousRouteAnalyzer", event_type=RuleEventType.SUSPICIOUS_ROUTE.value)
        # Track history of visited zones: track_id -> [(zone_name, timestamp)]
        self._track_zone_history: Dict[int, List[Tuple[str, float]]] = {}

    def evaluate(
        self,
        camera_id: int,
        detections: List[Detection],
        active_zones_by_track: Dict[int, List[Dict[str, Any]]],
        tripwire_breaches_by_track: Dict[int, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[BehaviorEvent]:
        self.total_evaluations += len(detections)
        events: List[BehaviorEvent] = []
        now = time.time()

        # Update zone sequence for each track
        for det in detections:
            zones = active_zones_by_track.get(det.track_id, [])
            if not zones:
                continue

            if det.track_id not in self._track_zone_history:
                self._track_zone_history[det.track_id] = []

            history = self._track_zone_history[det.track_id]
            for z in zones:
                zname = z.get("name", "")
                if not history or history[-1][0] != zname:
                    history.append((zname, now))

            # Keep last 8 zone visits
            if len(history) > 8:
                self._track_zone_history[det.track_id] = history[-8:]

            # If visited 3 or more distinct zones in under 45 seconds, trigger sequential route alert
            recent_zones = [h[0] for h in history if (now - h[1]) <= 45.0]
            if len(set(recent_zones)) >= 3:
                route_str = " -> ".join(recent_zones)
                ev = BehaviorEvent(
                    event_type=self.event_type,
                    camera_id=camera_id,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    severity=RuleSeverity.HIGH.value,
                    confidence=0.88,
                    details={
                        "route_sequence": recent_zones,
                        "summary": f"Multi-zone traversal pattern: {det.class_name} #{det.track_id} navigated {route_str}"
                    }
                )
                events.append(ev)
                self.total_events_generated += 1

        return events
