import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.event import DetectionEvent, RuleEvent
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.models.evidence import Evidence, EvidenceType
from app.core.event_bus import event_bus
from app.services.analytics.incident_intelligence import incident_intelligence
from app.services.notification_service import notification_service

logger = logging.getLogger("arc_vision.event_engine")

class EventEngine:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def process_frame_events(
        self,
        camera_id: int,
        camera_name: str,
        tracked_detections: List[Any],
        fired_rule_events: List[Dict[str, Any]],
        active_zones_map: Dict[int, List[int]],
        evidence_dict: Optional[Dict[str, Any]] = None,
        is_night_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Central processing pipeline:
        1. Persists DetectionEvents and RuleEvents to DB.
        2. Feeds events to IncidentIntelligence for correlation.
        3. Persists new/updated Incidents and linked Evidence records to DB.
        4. Broadcasts WebSocket notifications & dispatches alerts.
        """
        async with AsyncSessionLocal() as session:
            try:
                # 1. Persist Detection Events (sampled/filtered for high performance)
                for det in tracked_detections:
                    if det.confidence >= 0.40:
                        det_event = DetectionEvent(
                            camera_id=camera_id,
                            track_id=det.track_id,
                            object_class=det.class_name,
                            confidence=round(det.confidence, 3),
                            bbox_json=json.dumps({
                                "x1": round(det.box[0], 4),
                                "y1": round(det.box[1], 4),
                                "x2": round(det.box[2], 4),
                                "y2": round(det.box[3], 4)
                            }),
                            in_zone_ids=",".join(str(z) for z in active_zones_map.get(det.track_id, [])),
                            dwell_duration_sec=round(det.attributes.get("dwell_sec", 0.0), 1),
                            velocity_vector=f"{det.attributes.get('speed', 0.0):.2f}"
                        )
                        session.add(det_event)

                # 2. Persist Rule Events
                created_rule_events = []
                for fe in fired_rule_events:
                    re_obj = RuleEvent(
                        rule_id=fe.get("rule_id"),
                        camera_id=camera_id,
                        track_id=fe.get("track_id"),
                        event_type=fe.get("event_type", "RULE_BREACH"),
                        severity=fe.get("severity", "HIGH"),
                        description=fe.get("description", "Perimeter rule triggered"),
                        details_json=json.dumps(fe.get("details", {})),
                        is_correlated=False
                    )
                    session.add(re_obj)
                    created_rule_events.append(re_obj)

                await session.commit()

                # 3. Incident Correlation & Persistence
                correlated_incident = None
                for det in tracked_detections:
                    incident_candidate = incident_intelligence.correlate(
                        camera_id=camera_id,
                        camera_name=camera_name,
                        track_id=det.track_id,
                        object_class=det.class_name,
                        events=[fe for fe in fired_rule_events if fe.get("track_id") == det.track_id],
                        dwell_sec=det.attributes.get("dwell_sec", 0.0),
                        is_pacing=det.attributes.get("is_pacing", False),
                        is_night=is_night_mode,
                        active_zones=active_zones_map.get(det.track_id, [])
                    )

                    if incident_candidate:
                        code = incident_candidate["incident_code"]
                        # Check if incident already exists in DB
                        q = await session.execute(select(Incident).where(Incident.incident_code == code))
                        existing_inc = q.scalars().first()

                        if existing_inc:
                            # Update existing active incident
                            existing_inc.threat_score = max(existing_inc.threat_score, incident_candidate.get("threat_score", 85.0))
                            existing_inc.summary = incident_candidate["summary"]
                            db_inc = existing_inc
                        else:
                            # Create new persisted Incident
                            db_inc = Incident(
                                incident_code=code,
                                title=incident_candidate["title"],
                                summary=incident_candidate["summary"],
                                incident_type=incident_candidate["incident_type"],
                                camera_id=camera_id,
                                track_id=det.track_id,
                                severity=IncidentSeverity(incident_candidate["severity"]) if incident_candidate["severity"] in IncidentSeverity.__members__ else IncidentSeverity.HIGH,
                                status=IncidentStatus.DETECTED,
                                threat_score=incident_candidate.get("threat_score", 80.0),
                                location_name=camera_name,
                                tags_json=json.dumps(incident_candidate.get("tags", []))
                            )
                            session.add(db_inc)
                            await session.flush() # obtain db_inc.id

                        # 4. Attach & Persist Evidence Records if provided
                        if evidence_dict:
                            if "snapshot" in evidence_dict and evidence_dict["snapshot"]:
                                s = evidence_dict["snapshot"]
                                snap_ev = Evidence(
                                    incident_id=db_inc.id,
                                    camera_id=camera_id,
                                    file_type=EvidenceType.SNAPSHOT,
                                    file_path=s.get("url", ""),
                                    file_size_bytes=s.get("size_bytes", 0),
                                    sha256_hash=s.get("sha256", ""),
                                    metadata_json=json.dumps(s.get("meta", {}))
                                )
                                session.add(snap_ev)

                            if "clip" in evidence_dict and evidence_dict["clip"]:
                                c = evidence_dict["clip"]
                                clip_ev = Evidence(
                                    incident_id=db_inc.id,
                                    camera_id=camera_id,
                                    file_type=EvidenceType.CLIP,
                                    file_path=c.get("url", ""),
                                    file_size_bytes=c.get("size_bytes", 0),
                                    sha256_hash=c.get("sha256", ""),
                                    metadata_json=json.dumps(c.get("meta", {}))
                                )
                                session.add(clip_ev)

                            if "crop" in evidence_dict and evidence_dict["crop"]:
                                cr = evidence_dict["crop"]
                                cr_type_str = cr.get("file_type", "CROP_PERSON")
                                cr_type = EvidenceType[cr_type_str] if cr_type_str in EvidenceType.__members__ else EvidenceType.CROP_PERSON
                                crop_ev = Evidence(
                                    incident_id=db_inc.id,
                                    camera_id=camera_id,
                                    file_type=cr_type,
                                    file_path=cr.get("file_path", ""),
                                    file_size_bytes=cr.get("file_size_bytes", 0),
                                    sha256_hash=cr.get("sha256_hash", ""),
                                    metadata_json=json.dumps(cr.get("metadata", {}))
                                )
                                session.add(crop_ev)

                        await session.commit()
                        correlated_incident = incident_candidate
                        incident_candidate["db_id"] = db_inc.id

                        # 5. Broadcast to WebSockets and Notification Service
                        await event_bus.publish("incident:new", incident_candidate)
                        asyncio.create_task(notification_service.dispatch_incident_notification(incident_candidate))

                return correlated_incident

            except Exception as e:
                await session.rollback()
                logger.error(f"Error in EventEngine process_frame_events: {e}")
                return None

event_engine = EventEngine()
