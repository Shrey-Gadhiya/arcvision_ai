import json
import time
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

from app.services.ai.base import Detection
from app.models.rule import Rule, RuleEventType, RuleSeverity
from app.services.analytics.behavior import behavior_engine, BehaviorFeatureExtractor

logger = logging.getLogger("arc_vision.rule_evaluator")

class RuleEvaluator:
    """
    Evaluates configured user/operational rules against active detections,
    tracks, zones, tripwires, and behavior kinematics.
    """
    def __init__(self):
        # Key: rule_id -> timestamp of last fired event
        self._last_fired: Dict[int, float] = {}

    def is_rule_active_now(self, rule: Rule) -> bool:
        if not rule.is_active:
            return False

        try:
            sched = json.loads(rule.schedule_json) if isinstance(rule.schedule_json, str) else rule.schedule_json
            if not sched or sched.get("always", True):
                return True

            now_dt = datetime.now(timezone.utc)
            now_time = now_dt.strftime("%H:%M")
            start = sched.get("start_time", "00:00")
            end = sched.get("end_time", "23:59")

            if start <= end:
                return start <= now_time <= end
            else: # Overnight schedule, e.g. 20:00 to 06:00
                return now_time >= start or now_time <= end
        except Exception as e:
            logger.error(f"Error checking schedule for rule {rule.id}: {e}")
            return True

    def check_cooldown(self, rule_id: int, cooldown_sec: int) -> bool:
        now = time.time()
        last = self._last_fired.get(rule_id, 0.0)
        if (now - last) >= cooldown_sec:
            self._last_fired[rule_id] = now
            return True
        return False

    def evaluate(
        self,
        camera_id: int,
        rules: List[Rule],
        detection: Detection,
        active_zones: List[Dict[str, Any]],
        tripwire_breaches: List[Dict[str, Any]],
        is_night_mode: bool = False
    ) -> List[Dict[str, Any]]:
        fired_events: List[Dict[str, Any]] = []

        # Parse detection kinematics
        dwell = detection.attributes.get("dwell_sec", 0.0)
        is_stat = detection.attributes.get("is_stationary", False)
        pacing_count = detection.attributes.get("pacing_count", 0)
        vx, vy = detection.attributes.get("velocity", (0.0, 0.0))
        speed = math.hypot(vx, vy)
        traj = detection.attributes.get("trajectory", [])

        for rule in rules:
            if not self.is_rule_active_now(rule):
                continue

            # Check camera targeting
            try:
                target_cams = json.loads(rule.camera_ids_json) if isinstance(rule.camera_ids_json, str) else rule.camera_ids_json
                if target_cams and camera_id not in target_cams:
                    continue
            except Exception:
                pass

            # Parse rule conditions
            conds = {}
            if rule.conditions_json:
                try:
                    conds = json.loads(rule.conditions_json) if isinstance(rule.conditions_json, str) else rule.conditions_json
                except Exception:
                    conds = {}

            target_classes = conds.get("target_classes", [])
            if target_classes and detection.class_name.lower() not in [c.lower() for c in target_classes]:
                continue

            min_conf = conds.get("min_confidence", 0.35)
            if detection.confidence < min_conf:
                continue

            rule_fired = False
            event_details = {}

            # 1. Tripwire / Virtual Fence Crossing
            if rule.event_type in (RuleEventType.VIRTUAL_FENCE_CROSSING, RuleEventType.PERIMETER_BREACH):
                if tripwire_breaches:
                    for breach in tripwire_breaches:
                        rule_fired = True
                        event_details = {
                            "tripwire_name": breach["tripwire"].get("name"),
                            "crossing_direction": breach.get("crossing_direction"),
                            "track_id": detection.track_id,
                            "class_name": detection.class_name
                        }
                        break

            # 2. Zone Intrusion / Restricted Area Activity
            elif rule.event_type in (RuleEventType.ZONE_INTRUSION, RuleEventType.RESTRICTED_ZONE_ACTIVITY):
                target_zone_ids = conds.get("zones", [])
                matching_zones = [
                    z for z in active_zones
                    if (not target_zone_ids or z.get("id") in target_zone_ids) and z.get("zone_type") in ("RESTRICTED", "EXCLUSION", "BUFFER", "CHECKPOINT")
                ]
                if matching_zones:
                    rule_fired = True
                    event_details = {
                        "zone_name": matching_zones[0].get("name"),
                        "zone_id": matching_zones[0].get("id"),
                        "track_id": detection.track_id,
                        "class_name": detection.class_name,
                        "dwell_sec": dwell
                    }

            # 3. Loitering
            elif rule.event_type == RuleEventType.LOITERING:
                dwell_threshold = conds.get("min_dwell_sec", 15.0)
                if active_zones:
                    for z in active_zones:
                        z_thresh = z.get("loitering_time_sec", dwell_threshold)
                        if dwell >= z_thresh:
                            rule_fired = True
                            event_details = {
                                "zone_name": z.get("name"),
                                "dwell_sec": dwell,
                                "threshold_sec": z_thresh,
                                "summary": f"{detection.class_name} #{detection.track_id} loitering in {z.get('name')} for {dwell:.1f}s"
                            }
                            break
                elif dwell >= dwell_threshold:
                    rule_fired = True
                    event_details = {
                        "dwell_sec": dwell,
                        "threshold_sec": dwell_threshold,
                        "summary": f"{detection.class_name} #{detection.track_id} loitering for {dwell:.1f}s"
                    }

            # 4. Stationary Vehicle / Stationary Object
            elif rule.event_type in (RuleEventType.STATIONARY_VEHICLE, RuleEventType.UNUSUAL_VEHICLE_STOP):
                stat_thresh = conds.get("dwell_sec", 12.0)
                if detection.class_name.lower() in ("car", "truck", "bus", "motorcycle", "vehicle") and (is_stat or dwell >= stat_thresh):
                    rule_fired = True
                    event_details = {
                        "dwell_sec": dwell,
                        "is_stationary": True,
                        "summary": f"Stationary vehicle {detection.class_name} #{detection.track_id} stopped for {dwell:.1f}s"
                    }

            elif rule.event_type == RuleEventType.STATIONARY_OBJECT:
                stat_thresh = conds.get("dwell_sec", 10.0)
                if dwell >= stat_thresh:
                    rule_fired = True
                    event_details = {
                        "dwell_sec": dwell,
                        "is_stationary": True,
                        "summary": f"Stationary object {detection.class_name} #{detection.track_id} stationary for {dwell:.1f}s"
                    }

            # 5. Wrong-Way Movement
            elif rule.event_type == RuleEventType.WRONG_WAY:
                if tripwire_breaches:
                    for breach in tripwire_breaches:
                        tw = breach.get("tripwire", {})
                        req_dir = tw.get("direction", "BIDIRECTIONAL")
                        actual_dir = breach.get("crossing_direction")
                        if (req_dir == "A_TO_B" and actual_dir == "B_TO_A") or (req_dir == "B_TO_A" and actual_dir == "A_TO_B"):
                            rule_fired = True
                            event_details = {
                                "tripwire_name": tw.get("name"),
                                "expected_direction": req_dir,
                                "actual_direction": actual_dir,
                                "summary": f"{detection.class_name} #{detection.track_id} moved wrong-way across {tw.get('name')}"
                            }
                            break

            # 6. Night Movement
            elif rule.event_type == RuleEventType.NIGHT_MOVEMENT:
                if is_night_mode and detection.confidence >= min_conf:
                    rule_fired = True
                    event_details = {
                        "condition": "Night schedule movement",
                        "track_id": detection.track_id,
                        "confidence": detection.confidence,
                        "summary": f"Night movement detected: {detection.class_name} #{detection.track_id}"
                    }

            # 7. Repeated Movement (Pacing)
            elif rule.event_type == RuleEventType.REPEATED_MOVEMENT:
                min_revs = conds.get("min_reversals", 3)
                if pacing_count >= min_revs and dwell >= 8.0:
                    rule_fired = True
                    event_details = {
                        "reversals_count": pacing_count,
                        "dwell_sec": dwell,
                        "summary": f"Repeated movement detected ({pacing_count} direction reversals)"
                    }

            # 8. Rapid Movement
            elif rule.event_type == RuleEventType.RAPID_MOVEMENT:
                speed_thresh = conds.get("speed_threshold", 0.35)
                if speed >= speed_thresh:
                    rule_fired = True
                    event_details = {
                        "speed_units_sec": round(speed, 3),
                        "speed_threshold": speed_thresh,
                        "summary": f"Rapid movement detected ({speed:.2f} units/s)"
                    }

            # 9. Abandoned Object
            elif rule.event_type == RuleEventType.ABANDONED_OBJECT:
                if detection.class_name.lower() in ("backpack", "suitcase", "handbag", "package", "box") and dwell >= 12.0:
                    rule_fired = True
                    event_details = {
                        "dwell_sec": dwell,
                        "summary": f"Unattended {detection.class_name} #{detection.track_id} stationary for {dwell:.1f}s"
                    }

            # 10. Suspicious Route
            elif rule.event_type == RuleEventType.SUSPICIOUS_ROUTE:
                req_route = conds.get("route_sequence", [])
                if len(active_zones) >= 2 or len(req_route) > 0:
                    rule_fired = True
                    event_details = {
                        "active_zones": [z.get("name") for z in active_zones],
                        "summary": f"Suspicious route traversal pattern for {detection.class_name} #{detection.track_id}"
                    }

            if rule_fired:
                if self.check_cooldown(rule.id, rule.cooldown_seconds):
                    fired_events.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "event_type": rule.event_type.value,
                        "severity": rule.severity.value,
                        "camera_id": camera_id,
                        "track_id": detection.track_id,
                        "details": event_details
                    })

        return fired_events

rule_evaluator = RuleEvaluator()
