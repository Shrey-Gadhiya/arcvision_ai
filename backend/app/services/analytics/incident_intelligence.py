import uuid
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
from app.models.incident import Incident, IncidentStatus, IncidentSeverity

logger = logging.getLogger("arc_vision.incident_intelligence")

class IncidentIntelligenceEngine:
    """
    Correlates multi-modal behavioral, spatial, and temporal signals:
    Detection + Zone + Tripwire + Dwell + Pacing + Night + Wrong-Way + Loitering
    into unified, explainable tactical Incidents with full timeline auditability.
    """
    def __init__(self):
        # Key: (camera_id, track_id) -> state dict
        self._active_correlations: Dict[Any, Dict[str, Any]] = {}
        self._incident_counter = 100

    def correlate(
        self,
        camera_id: int,
        camera_name: str,
        track_id: int,
        object_class: str,
        events: List[Dict[str, Any]],
        dwell_sec: float,
        is_pacing: bool = False,
        is_night: bool = False,
        active_zones: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        if not events and dwell_sec < 10.0:
            return None

        active_zones = active_zones or []
        corr_key = (camera_id, track_id)
        now = time.time()
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if corr_key not in self._active_correlations:
            self._active_correlations[corr_key] = {
                "start_time": now,
                "last_update": now,
                "signals": set(),
                "event_ids": [],
                "timeline": [],
                "highest_severity": IncidentSeverity.MEDIUM,
                "incident_created": False,
                "incident_id": None
            }

        corr = self._active_correlations[corr_key]
        corr["last_update"] = now

        # Ingest new events and append to timeline
        for ev in events:
            etype = ev.get("event_type", "UNKNOWN")
            corr["signals"].add(etype)
            if ev.get("rule_id"):
                corr["event_ids"].append(ev.get("rule_id"))

            det_str = ev.get("details", {}).get("summary") or f"{etype} detected"
            corr["timeline"].append({
                "time": now_str,
                "signal": etype,
                "description": det_str
            })

        # Calculate explainable threat score (0 to 100) with itemized breakdown
        score_breakdown: Dict[str, float] = {"base_detection": 30.0}
        score = 30.0

        if "VIRTUAL_FENCE_CROSSING" in corr["signals"] or "PERIMETER_BREACH" in corr["signals"]:
            score += 35.0
            score_breakdown["perimeter_breach"] = 35.0

        if "ZONE_INTRUSION" in corr["signals"] or "RESTRICTED_ZONE_ACTIVITY" in corr["signals"]:
            score += 25.0
            score_breakdown["restricted_zone"] = 25.0

        if any(z.get("zone_type") in ("RESTRICTED", "EXCLUSION") for z in active_zones):
            score += 20.0
            score_breakdown["restricted_zone_occupancy"] = 20.0

        if "WRONG_WAY" in corr["signals"]:
            score += 20.0
            score_breakdown["wrong_way"] = 20.0

        if "LOITERING" in corr["signals"]:
            score += 15.0
            score_breakdown["loitering"] = 15.0

        if "RAPID_MOVEMENT" in corr["signals"]:
            score += 15.0
            score_breakdown["rapid_movement"] = 15.0

        if "REPEATED_MOVEMENT" in corr["signals"] or is_pacing:
            score += 15.0
            score_breakdown["repeated_movement"] = 15.0

        if "ABANDONED_OBJECT" in corr["signals"]:
            score += 30.0
            score_breakdown["abandoned_object"] = 30.0

        if "FIRE_DETECTED" in corr["signals"]:
            score += 45.0
            score_breakdown["fire_detection"] = 45.0

        if "SMOKE_DETECTED" in corr["signals"]:
            score += 35.0
            score_breakdown["smoke_detection"] = 35.0

        if "FALL_DETECTED" in corr["signals"]:
            score += 40.0
            score_breakdown["fall_detection"] = 40.0

        if "DANGEROUS_OBJECT_DETECTED" in corr["signals"]:
            score += 50.0
            score_breakdown["dangerous_object_weapon"] = 50.0

        if "CROWD_DENSITY" in corr["signals"] or "CROWD_FORMATION" in corr["signals"] or "CROWD_DENSITY_THRESHOLD" in corr["signals"]:
            score += 20.0
            score_breakdown["crowd_formation"] = 20.0

        if "ACTION_DETECTED" in corr["signals"]:
            score += 20.0
            score_breakdown["action_recognition"] = 20.0

        if is_night:
            score += 15.0
            score_breakdown["night_schedule"] = 15.0

        if dwell_sec > 25.0:
            score += 10.0
            score_breakdown["extended_dwell"] = 10.0

        score = min(100.0, score)

        # Trigger incident when threat score >= 65 and incident hasn't been emitted yet for this track
        if score >= 65.0 and not corr["incident_created"]:
            corr["incident_created"] = True
            self._incident_counter += 1
            code = f"INC-{datetime.now(timezone.utc).year}-{self._incident_counter:04d}"

            # Classify severity
            if score >= 85.0:
                severity = IncidentSeverity.CRITICAL
                title = f"CRITICAL SECURITY ALERT: {object_class.upper()} BREACH (Track #{track_id})"
            elif score >= 70.0:
                severity = IncidentSeverity.HIGH
                title = f"HIGH-RISK BEHAVIOR ALERT: {object_class.upper()} (Track #{track_id})"
            else:
                severity = IncidentSeverity.MEDIUM
                title = f"SUSPICIOUS ACTIVITY IN SECTOR: {object_class.upper()} (Track #{track_id})"

            timeline_summary = " | ".join([f"[{t['time']}] {t['description']}" for t in corr["timeline"][-4:]])
            summary = (
                f"Multi-sensor correlation detected {object_class} (Track #{track_id}) at {camera_name}. "
                f"Signals: {', '.join(sorted(corr['signals']))}. "
                f"Dwell: {round(dwell_sec, 1)}s. "
                f"Threat Score: {int(score)}/100 (Explainable Factors: {', '.join(f'{k}: +{int(v)}' for k, v in score_breakdown.items())}). "
                f"Timeline: {timeline_summary}"
            )

            incident_payload = {
                "incident_code": code,
                "title": title,
                "summary": summary,
                "incident_type": "BEHAVIOR_INTRUSION",
                "camera_id": camera_id,
                "track_id": track_id,
                "severity": severity,
                "status": IncidentStatus.NEW,
                "threat_score": score,
                "location_name": camera_name,
                "correlated_event_ids": ",".join(str(e) for e in corr["event_ids"]),
                "tags": [object_class] + list(corr["signals"])[:4] + (["night"] if is_night else []),
                "timeline": corr["timeline"],
                "score_breakdown": score_breakdown
            }

            return incident_payload

        # Evict stale states older than 60s
        stale_keys = [k for k, v in self._active_correlations.items() if (now - v["last_update"]) > 60.0]
        for k in stale_keys:
            del self._active_correlations[k]

        return None

incident_intelligence = IncidentIntelligenceEngine()
