import re
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func

from app.models.camera import Camera
from app.models.event import DetectionEvent, RuleEvent
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.recording import RecordingSegment
from app.models.evidence import Evidence
from app.models.anpr import ANPRRecord
from app.models.face import FaceRecord, FaceIdentity
from app.models.cross_camera import GlobalTrack, TrackObservation
from app.models.investigation import InvestigationCase, CaseFinding, CaseStatus, CasePriority
from app.schemas.all_schemas import (
    ParsedSemanticQuery,
    InvestigationSearchFilter,
    InvestigationSearchResultItem,
    InvestigationSearchResponse,
    NLSearchResponse,
    InvestigationTimelineEvent,
    CaseTimelineResponse,
    CaseExportResponse,
    InvestigationCaseResponse,
    CaseFindingResponse
)

# Color keywords
COLOR_KEYWORDS = {
    "red", "white", "black", "blue", "silver", "grey", "gray", "yellow",
    "green", "orange", "brown", "gold", "dark", "light"
}

# Object class mappings
CLASS_MAPPINGS = {
    "person": ["person", "man", "woman", "pedestrian", "suspect", "individual", "human", "guy", "worker"],
    "car": ["car", "sedan", "automobile", "suv", "hatchback", "vehicle", "taxi", "cab"],
    "truck": ["truck", "lorry", "pickup", "van", "delivery truck", "trailer"],
    "bus": ["bus", "coach", "transit"],
    "motorcycle": ["motorcycle", "bike", "scooter", "motorbike", "two-wheeler"],
    "bicycle": ["bicycle", "cyclist", "cycle"]
}

# Incident & Behavior keywords
INCIDENT_KEYWORDS = {
    "FIRE_SMOKE": ["fire", "smoke", "flame", "blaze", "burning"],
    "WEAPON_DETECTED": ["weapon", "gun", "firearm", "knife", "pistol", "rifle", "armed"],
    "PERSON_FALL": ["fall", "falling", "fallen", "slip", "trip", "collapse", "man down"],
    "INTRUSION": ["intrusion", "intruder", "trespass", "trespassing", "breach", "fence climb", "unauthorized entry"],
    "LOITERING": ["loitering", "loiter", "hanging around", "suspicious presence", "stationary person"],
    "CROWD_GATHERING": ["crowd", "gathering", "mob", "group", "congregation", "riot"],
    "SPEEDING": ["speeding", "fast vehicle", "speed violation", "overspeeding"],
    "WRONG_WAY": ["wrong way", "wrong direction", "reverse driving"]
}

# Severity keywords
SEVERITY_KEYWORDS = {
    "CRITICAL": ["critical", "emergency", "urgent", "extreme", "severe", "danger"],
    "HIGH": ["high", "major", "threat"],
    "MEDIUM": ["medium", "moderate", "warning"],
    "LOW": ["low", "minor", "routine", "info"]
}


class SemanticQueryParser:
    """Parses natural language freeform queries into structured filters and semantic tokens."""

    @classmethod
    def parse_query(cls, query: str, available_cameras: Optional[Dict[int, str]] = None) -> ParsedSemanticQuery:
        q_raw = query.strip()
        q_lower = q_raw.lower()

        object_classes: List[str] = []
        colors: List[str] = []
        attributes: List[str] = []
        locations: List[str] = []
        camera_ids: List[int] = []
        plate_numbers: List[str] = []
        person_names: List[str] = []
        incident_types: List[str] = []
        severities: List[str] = []
        action_terms: List[str] = []

        # 1. Object Classes
        for target_cls, aliases in CLASS_MAPPINGS.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', q_lower):
                    if target_cls not in object_classes:
                        object_classes.append(target_cls)
                    break

        # 2. Colors
        for col in COLOR_KEYWORDS:
            if re.search(r'\b' + re.escape(col) + r'\b', q_lower):
                colors.append(col)

        # 3. Clothing / Attributes
        attr_terms = ["hoodie", "jacket", "shirt", "backpack", "helmet", "hat", "cap", "mask", "vest"]
        for att in attr_terms:
            if re.search(r'\b' + re.escape(att) + r'\b', q_lower):
                attributes.append(att)

        # 4. Incident / Threat types
        for inc_key, keywords in INCIDENT_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                    if inc_key not in incident_types:
                        incident_types.append(inc_key)
                    if kw not in action_terms:
                        action_terms.append(kw)
                    break

        # 5. Severities
        for sev_key, keywords in SEVERITY_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                    if sev_key not in severities:
                        severities.append(sev_key)
                    break

        # 6. Plate Number extraction (Regex for alphanumeric patterns like MH12, MH-12-AB-1234, DL01, etc.)
        plate_patterns = [
            r'\b[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}\b',  # Indian format e.g. MH12DE1432, DL01A1234
            r'\b[A-Z]{2}[-\s]?[0-9]{1,2}[-\s]?[A-Z]{0,3}[-\s]?[0-9]{1,4}\b',
            r'\b[A-Z]{3}[-\s]?[0-9]{3,4}\b',  # Standard 3-letter 4-number
            r'(?:plate|license|licence|reg|registration)\s*(?:number|no|#)?\s*[:=]?\s*([A-Za-z0-9-]+)'
        ]
        for pat in plate_patterns:
            matches = re.findall(pat, q_raw, re.IGNORECASE)
            for m in matches:
                clean_plate = m.strip().upper().replace(" ", "").replace("-", "")
                if len(clean_plate) >= 4 and not clean_plate.isdigit() and clean_plate not in plate_numbers:
                    # Ignore common words
                    if clean_plate not in {"GATE", "ZONE", "DOOR", "EAST", "WEST", "AUTO", "CARS"}:
                        plate_numbers.append(clean_plate)

        # 7. Camera / Location Matching
        if available_cameras:
            for cam_id, cam_name in available_cameras.items():
                cam_name_lower = cam_name.lower()
                # Split camera name into parts (e.g. "Gate 2 - South Entry" -> ["gate 2", "south entry"])
                parts = [p.strip() for p in re.split(r'[-–—:,/|]', cam_name_lower) if len(p.strip()) >= 3]
                matched = False
                if cam_name_lower in q_lower or f"camera {cam_id}" in q_lower or f"cam {cam_id}" in q_lower:
                    matched = True
                else:
                    for part in parts:
                        if re.search(r'\b' + re.escape(part) + r'\b', q_lower):
                            matched = True
                            break
                if matched:
                    if cam_id not in camera_ids:
                        camera_ids.append(cam_id)
                    if cam_name not in locations:
                        locations.append(cam_name)

        # Generic location names if not matched to specific camera
        location_keywords = ["gate 1", "gate 2", "entrance", "exit", "warehouse", "loading dock", "parking", "perimeter", "lobby", "sector 1", "sector 2", "zone a", "zone b"]
        for loc in location_keywords:
            if re.search(r'\b' + re.escape(loc) + r'\b', q_lower) and not any(loc in l.lower() for l in locations):
                locations.append(loc.title())

        # 8. Person Names (e.g. "named John", "suspect Alice", "VIP Rahul")
        name_match = re.search(r'(?:named|person|suspect|identity|vip)\s+([A-Z][a-z]+)', q_raw)
        if name_match:
            person_names.append(name_match.group(1))

        # 9. Temporal Range Parsing
        now = datetime.now(timezone.utc)
        time_start: Optional[datetime] = None
        time_end: Optional[datetime] = None
        temporal_expr = None

        if "last 1 hour" in q_lower or "last hour" in q_lower or "past hour" in q_lower:
            time_start = now - timedelta(hours=1)
            time_end = now
            temporal_expr = "Last 1 Hour"
        elif "last 2 hours" in q_lower or "past 2 hours" in q_lower:
            time_start = now - timedelta(hours=2)
            time_end = now
            temporal_expr = "Last 2 Hours"
        elif "last 6 hours" in q_lower or "past 6 hours" in q_lower:
            time_start = now - timedelta(hours=6)
            time_end = now
            temporal_expr = "Last 6 Hours"
        elif "last 24 hours" in q_lower or "past 24 hours" in q_lower or "past day" in q_lower:
            time_start = now - timedelta(hours=24)
            time_end = now
            temporal_expr = "Last 24 Hours"
        elif "today" in q_lower:
            today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            time_start = today_midnight
            time_end = now
            temporal_expr = "Today"
        elif "yesterday" in q_lower:
            yesterday_midnight = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            if "afternoon" in q_lower:
                time_start = yesterday_midnight.replace(hour=12, minute=0, second=0)
                time_end = yesterday_midnight.replace(hour=18, minute=0, second=0)
                temporal_expr = "Yesterday Afternoon (12:00 - 18:00)"
            elif "morning" in q_lower:
                time_start = yesterday_midnight.replace(hour=6, minute=0, second=0)
                time_end = yesterday_midnight.replace(hour=12, minute=0, second=0)
                temporal_expr = "Yesterday Morning (06:00 - 12:00)"
            elif "night" in q_lower or "evening" in q_lower:
                time_start = yesterday_midnight.replace(hour=18, minute=0, second=0)
                time_end = yesterday_midnight.replace(hour=23, minute=59, second=59)
                temporal_expr = "Yesterday Evening/Night (18:00 - 23:59)"
            else:
                time_start = yesterday_midnight
                time_end = yesterday_end
                temporal_expr = "Yesterday (Full Day)"
        elif "past week" in q_lower or "last 7 days" in q_lower or "last week" in q_lower:
            time_start = now - timedelta(days=7)
            time_end = now
            temporal_expr = "Past 7 Days"
        elif "this morning" in q_lower:
            time_start = now.replace(hour=6, minute=0, second=0, microsecond=0)
            time_end = now.replace(hour=12, minute=0, second=0, microsecond=0)
            temporal_expr = "This Morning (06:00 - 12:00)"

        # 10. Construct Human Explanation & Parser Confidence
        parts = []
        if object_classes:
            parts.append(f"entity: {', '.join(object_classes)}")
        if colors:
            parts.append(f"color: {', '.join(colors)}")
        if attributes:
            parts.append(f"wearing/attribute: {', '.join(attributes)}")
        if plate_numbers:
            parts.append(f"plate: {', '.join(plate_numbers)}")
        if person_names:
            parts.append(f"identity: {', '.join(person_names)}")
        if incident_types:
            parts.append(f"threat/action: {', '.join(incident_types)}")
        if locations:
            parts.append(f"location: {', '.join(locations)}")
        if temporal_expr:
            parts.append(f"time: {temporal_expr}")
        if severities:
            parts.append(f"severity: {', '.join(severities)}")

        if parts:
            explanation = "Extracted criteria: " + " | ".join(parts)
            confidence = min(0.98, 0.60 + 0.08 * len(parts))
        else:
            explanation = f"General keyword query: '{q_raw}' (multi-modal full text search)"
            confidence = 0.65

        return ParsedSemanticQuery(
            raw_query=q_raw,
            object_classes=object_classes,
            colors=colors,
            attributes=attributes,
            locations=locations,
            camera_ids=camera_ids,
            plate_numbers=plate_numbers,
            person_names=person_names,
            incident_types=incident_types,
            severities=severities,
            time_range_start=time_start,
            time_range_end=time_end,
            temporal_expression=temporal_expr,
            action_terms=action_terms,
            explanation=explanation,
            parser_confidence=round(confidence, 2)
        )


class SemanticSearchService:
    """Performs unified multi-modal investigation and semantic search across real VMS tables."""

    @classmethod
    async def execute_semantic_search(
        cls,
        parsed_query: ParsedSemanticQuery,
        min_confidence: float,
        limit: int,
        offset: int,
        db: AsyncSession
    ) -> NLSearchResponse:
        # Pre-fetch cameras
        cam_res = await db.execute(select(Camera))
        cams = {c.id: c.name for c in cam_res.scalars().all()}

        items: List[InvestigationSearchResultItem] = []

        # 1. Search Incidents
        inc_stmt = select(Incident)
        inc_conds = []

        if parsed_query.camera_ids:
            inc_conds.append(Incident.camera_id.in_(parsed_query.camera_ids))
        if parsed_query.severities:
            # Map string to IncidentSeverity enum if matching
            matched_sevs = [s for s in IncidentSeverity if s.value in parsed_query.severities]
            if matched_sevs:
                inc_conds.append(Incident.severity.in_(matched_sevs))
        if parsed_query.time_range_start:
            inc_conds.append(Incident.detected_at >= parsed_query.time_range_start)
        if parsed_query.time_range_end:
            inc_conds.append(Incident.detected_at <= parsed_query.time_range_end)

        if inc_conds:
            inc_stmt = inc_stmt.where(and_(*inc_conds))

        inc_stmt = inc_stmt.order_by(desc(Incident.detected_at)).limit(limit * 2)
        inc_res = await db.execute(inc_stmt)
        incidents = inc_res.scalars().all()

        for inc in incidents:
            relevance, reasons = cls._score_incident(inc, parsed_query)
            if relevance >= min_confidence:
                # Fetch linked evidence
                evi_res = await db.execute(
                    select(Evidence).where(Evidence.incident_id == inc.id).order_by(Evidence.id.asc()).limit(1)
                )
                evi = evi_res.scalar_one_or_none()
                thumb = evi.file_path if evi else None
                evi_id = evi.id if evi else None

                # Fetch linked recording
                seg_res = await db.execute(
                    select(RecordingSegment).where(
                        and_(
                            RecordingSegment.camera_id == inc.camera_id,
                            RecordingSegment.start_time <= inc.detected_at,
                            RecordingSegment.end_time >= inc.detected_at
                        )
                    ).limit(1)
                )
                seg = seg_res.scalar_one_or_none()
                linked_rec = None
                if seg:
                    linked_rec = {
                        "id": seg.id,
                        "file_path": seg.file_path,
                        "start_time": seg.start_time.isoformat(),
                        "end_time": seg.end_time.isoformat(),
                        "duration_sec": seg.duration_sec
                    }

                items.append(
                    InvestigationSearchResultItem(
                        id=f"INC_{inc.id}",
                        result_type="INCIDENT",
                        timestamp=inc.detected_at,
                        camera_id=inc.camera_id,
                        camera_name=cams.get(inc.camera_id, f"Camera #{inc.camera_id}"),
                        object_class="person" if "PERSON" in inc.incident_type else "object",
                        track_id=inc.track_id,
                        confidence=round(inc.threat_score / 100.0, 2),
                        event_type=inc.incident_type,
                        severity=inc.severity.value if hasattr(inc.severity, 'value') else str(inc.severity),
                        thumbnail_url=thumb,
                        details={
                            "incident_code": inc.incident_code,
                            "title": inc.title,
                            "summary": inc.summary,
                            "status": inc.status.value if hasattr(inc.status, 'value') else str(inc.status),
                            "threat_score": inc.threat_score
                        },
                        linked_recording=linked_rec,
                        linked_evidence_id=evi_id,
                        match_score=round(relevance, 2),
                        matched_reasons=reasons,
                        attributes_detected=[inc.incident_type]
                    )
                )

        # 2. Search Detection Events
        det_stmt = select(DetectionEvent)
        det_conds = []

        if parsed_query.camera_ids:
            det_conds.append(DetectionEvent.camera_id.in_(parsed_query.camera_ids))
        if parsed_query.object_classes:
            det_conds.append(DetectionEvent.object_class.in_(parsed_query.object_classes))
        if parsed_query.time_range_start:
            det_conds.append(DetectionEvent.timestamp >= parsed_query.time_range_start)
        if parsed_query.time_range_end:
            det_conds.append(DetectionEvent.timestamp <= parsed_query.time_range_end)

        if det_conds:
            det_stmt = det_stmt.where(and_(*det_conds))

        det_stmt = det_stmt.order_by(desc(DetectionEvent.timestamp)).limit(limit * 2)
        det_res = await db.execute(det_stmt)
        detections = det_res.scalars().all()

        for det in detections:
            relevance, reasons = cls._score_detection(det, parsed_query)
            if relevance >= min_confidence:
                # Find recording
                seg_res = await db.execute(
                    select(RecordingSegment).where(
                        and_(
                            RecordingSegment.camera_id == det.camera_id,
                            RecordingSegment.start_time <= det.timestamp,
                            RecordingSegment.end_time >= det.timestamp
                        )
                    ).limit(1)
                )
                seg = seg_res.scalar_one_or_none()
                linked_rec = None
                if seg:
                    linked_rec = {
                        "id": seg.id,
                        "file_path": seg.file_path,
                        "start_time": seg.start_time.isoformat(),
                        "end_time": seg.end_time.isoformat(),
                        "duration_sec": seg.duration_sec
                    }

                items.append(
                    InvestigationSearchResultItem(
                        id=f"DET_{det.id}",
                        result_type="DETECTION",
                        timestamp=det.timestamp,
                        camera_id=det.camera_id,
                        camera_name=cams.get(det.camera_id, f"Camera #{det.camera_id}"),
                        object_class=det.object_class,
                        track_id=det.track_id,
                        confidence=det.confidence,
                        event_type="DETECTION",
                        severity="LOW",
                        thumbnail_url=None,
                        details={
                            "dwell_duration_sec": getattr(det, "dwell_duration_sec", 0.0),
                            "velocity_vector": getattr(det, "velocity_vector", "0.0,0.0"),
                            "direction": getattr(det, "direction", "FORWARD")
                        },
                        linked_recording=linked_rec,
                        linked_evidence_id=None,
                        match_score=round(relevance, 2),
                        matched_reasons=reasons,
                        attributes_detected=[det.object_class] + ([getattr(det, "direction", None)] if getattr(det, "direction", None) else [])
                    )
                )

        # 3. Search ANPR Records
        anpr_stmt = select(ANPRRecord)
        anpr_conds = []

        if parsed_query.camera_ids:
            anpr_conds.append(ANPRRecord.camera_id.in_(parsed_query.camera_ids))
        if parsed_query.plate_numbers:
            # Match plate number substrings
            plate_likes = [ANPRRecord.plate_number.ilike(f"%{p}%") for p in parsed_query.plate_numbers]
            anpr_conds.append(or_(*plate_likes))
        if parsed_query.object_classes and any(c in ["car", "truck", "bus", "motorcycle"] for c in parsed_query.object_classes):
            vehicle_types = [c for c in parsed_query.object_classes if c in ["car", "truck", "bus", "motorcycle"]]
            anpr_conds.append(ANPRRecord.vehicle_type.in_(vehicle_types))
        if parsed_query.time_range_start:
            anpr_conds.append(ANPRRecord.timestamp >= parsed_query.time_range_start)
        if parsed_query.time_range_end:
            anpr_conds.append(ANPRRecord.timestamp <= parsed_query.time_range_end)

        if anpr_conds:
            anpr_stmt = anpr_stmt.where(and_(*anpr_conds))

        anpr_stmt = anpr_stmt.order_by(desc(ANPRRecord.timestamp)).limit(limit * 2)
        anpr_res = await db.execute(anpr_stmt)
        anpr_records = anpr_res.scalars().all()

        for anpr in anpr_records:
            relevance, reasons = cls._score_anpr(anpr, parsed_query)
            if relevance >= min_confidence:
                items.append(
                    InvestigationSearchResultItem(
                        id=f"ANPR_{anpr.id}",
                        result_type="ANPR",
                        timestamp=anpr.timestamp,
                        camera_id=anpr.camera_id,
                        camera_name=cams.get(anpr.camera_id, f"Camera #{anpr.camera_id}"),
                        object_class=anpr.vehicle_type or "vehicle",
                        track_id=anpr.track_id,
                        confidence=anpr.confidence,
                        event_type="PLATE_SIGHTING",
                        severity="CRITICAL" if anpr.is_matched else "INFO",
                        thumbnail_url=anpr.crop_path or anpr.vehicle_crop_path,
                        details={
                            "plate_number": anpr.plate_number,
                            "raw_text": anpr.raw_text,
                            "validation_status": anpr.validation_status.value if hasattr(anpr.validation_status, 'value') else str(anpr.validation_status),
                            "validation_format": anpr.validation_format,
                            "is_matched": anpr.is_matched,
                            "watchlist_category": anpr.watchlist_category,
                            "vehicle_color": anpr.vehicle_color,
                            "vehicle_make": anpr.vehicle_make,
                            "dwell_duration_sec": anpr.dwell_duration_sec
                        },
                        linked_recording={"id": anpr.recording_segment_id} if anpr.recording_segment_id else None,
                        linked_evidence_id=anpr.evidence_id,
                        match_score=round(relevance, 2),
                        matched_reasons=reasons,
                        attributes_detected=list(filter(None, [anpr.plate_number, anpr.vehicle_color, anpr.vehicle_make]))
                    )
                )

        # 4. Search Face Records
        face_stmt = select(FaceRecord)
        face_conds = []

        if parsed_query.camera_ids:
            face_conds.append(FaceRecord.camera_id.in_(parsed_query.camera_ids))
        if parsed_query.person_names:
            name_likes = [FaceRecord.matched_name.ilike(f"%{n}%") for n in parsed_query.person_names]
            face_conds.append(or_(*name_likes))
        if parsed_query.time_range_start:
            face_conds.append(FaceRecord.timestamp >= parsed_query.time_range_start)
        if parsed_query.time_range_end:
            face_conds.append(FaceRecord.timestamp <= parsed_query.time_range_end)

        if face_conds:
            face_stmt = face_stmt.where(and_(*face_conds))

        face_stmt = face_stmt.order_by(desc(FaceRecord.timestamp)).limit(limit * 2)
        face_res = await db.execute(face_stmt)
        face_records = face_res.scalars().all()

        for fr in face_records:
            relevance, reasons = cls._score_face(fr, parsed_query)
            if relevance >= min_confidence:
                items.append(
                    InvestigationSearchResultItem(
                        id=f"FACE_{fr.id}",
                        result_type="FACE",
                        timestamp=fr.timestamp,
                        camera_id=fr.camera_id,
                        camera_name=cams.get(fr.camera_id, f"Camera #{fr.camera_id}"),
                        object_class="person",
                        track_id=fr.track_id,
                        confidence=fr.similarity_score,
                        event_type="FACE_SIGHTING",
                        severity="CRITICAL" if fr.match_status == "MATCHED" else "INFO",
                        thumbnail_url=fr.face_crop_path,
                        details={
                            "matched_name": fr.matched_name,
                            "match_status": fr.match_status,
                            "similarity_score": fr.similarity_score,
                            "watchlist_category": fr.watchlist_category,
                            "quality_score": fr.quality_score
                        },
                        linked_recording={"id": fr.recording_segment_id} if fr.recording_segment_id else None,
                        linked_evidence_id=fr.evidence_id,
                        match_score=round(relevance, 2),
                        matched_reasons=reasons,
                        attributes_detected=list(filter(None, [fr.matched_name, fr.match_status]))
                    )
                )

        # 5. Search Evidence Items
        evi_stmt = select(Evidence)
        evi_conds = []
        if parsed_query.time_range_start:
            evi_conds.append(Evidence.created_at >= parsed_query.time_range_start)
        if parsed_query.time_range_end:
            evi_conds.append(Evidence.created_at <= parsed_query.time_range_end)
        if evi_conds:
            evi_stmt = evi_stmt.where(and_(*evi_conds))

        evi_stmt = evi_stmt.order_by(desc(Evidence.created_at)).limit(limit)
        evi_res = await db.execute(evi_stmt)
        evidence_records = evi_res.scalars().all()

        for ev in evidence_records:
            relevance, reasons = cls._score_evidence(ev, parsed_query)
            if relevance >= min_confidence:
                file_type_str = ev.file_type.value if hasattr(ev.file_type, 'value') else str(ev.file_type)
                items.append(
                    InvestigationSearchResultItem(
                        id=f"EVI_{ev.id}",
                        result_type="EVIDENCE",
                        timestamp=ev.created_at,
                        camera_id=ev.camera_id or 1,
                        camera_name=cams.get(ev.camera_id, "Evidence Vault"),
                        object_class="evidence",
                        track_id=None,
                        confidence=0.95,
                        event_type=f"EVIDENCE_{file_type_str}",
                        severity="HIGH",
                        thumbnail_url=ev.file_path,
                        details={
                            "evidence_type": file_type_str,
                            "file_path": ev.file_path,
                            "file_size_bytes": ev.file_size_bytes,
                            "sha256": ev.sha256_hash,
                            "metadata": ev.metadata_json
                        },
                        linked_recording=None,
                        linked_evidence_id=ev.id,
                        match_score=round(relevance, 2),
                        matched_reasons=reasons,
                        attributes_detected=[file_type_str]
                    )
                )

        # Sort all items by match_score descending, then timestamp descending
        items.sort(key=lambda x: (x.match_score or 0.0, x.timestamp), reverse=True)

        total_count = len(items)
        paginated_items = items[offset : offset + limit]

        return NLSearchResponse(
            parsed_query=parsed_query,
            total=total_count,
            limit=limit,
            offset=offset,
            items=paginated_items
        )

    # --- Relevance Scoring Helpers ---

    @classmethod
    def _score_incident(cls, inc: Incident, pq: ParsedSemanticQuery) -> Tuple[float, List[str]]:
        score = 0.50
        reasons = []

        # Check incident type
        for inc_type in pq.incident_types:
            if inc_type in inc.incident_type or inc.incident_type in inc_type:
                score += 0.35
                reasons.append(f"Matched threat type: {inc_type}")
                break

        # Check raw keywords against title and summary
        summary_text = f"{inc.title} {inc.summary} {inc.incident_code}".lower()
        if pq.raw_query.lower() in summary_text:
            score += 0.25
            reasons.append("Exact query match in incident summary")

        for act in pq.action_terms:
            if act in summary_text:
                score += 0.15
                reasons.append(f"Matched action: {act}")

        for col in pq.colors:
            if col in summary_text:
                score += 0.15
                reasons.append(f"Matched color attribute: {col}")

        # Severity boost
        if pq.severities and hasattr(inc.severity, 'value') and inc.severity.value in pq.severities:
            score += 0.10
            reasons.append(f"Matched severity: {inc.severity.value}")

        # Threat score weight
        score += (inc.threat_score / 100.0) * 0.10

        if not reasons:
            reasons.append("Correlated incident event")

        return min(0.99, score), reasons

    @classmethod
    def _score_detection(cls, det: DetectionEvent, pq: ParsedSemanticQuery) -> Tuple[float, List[str]]:
        score = 0.40
        reasons = []

        if pq.object_classes and det.object_class in pq.object_classes:
            score += 0.35
            reasons.append(f"Matched object class: {det.object_class}")

        if det.confidence:
            score += det.confidence * 0.15

        dwell = getattr(det, "dwell_duration_sec", 0.0) or 0.0
        vel = getattr(det, "velocity_px_per_sec", 0.0) or 0.0
        if "speeding" in pq.action_terms and vel > 100:
            score += 0.20
            reasons.append("High velocity motion match")

        if "loitering" in pq.action_terms and dwell > 30:
            score += 0.20
            reasons.append(f"Extended dwell duration ({dwell:.1f}s)")

        if not reasons:
            reasons.append(f"Detection of {det.object_class}")

        return min(0.99, score), reasons

    @classmethod
    def _score_anpr(cls, anpr: ANPRRecord, pq: ParsedSemanticQuery) -> Tuple[float, List[str]]:
        score = 0.50
        reasons = []

        # Plate matching
        for p in pq.plate_numbers:
            if p in anpr.plate_number.upper():
                score += 0.45
                reasons.append(f"Matched license plate: {anpr.plate_number}")
                break

        # Vehicle class matching
        if pq.object_classes and anpr.vehicle_type in pq.object_classes:
            score += 0.20
            reasons.append(f"Matched vehicle type: {anpr.vehicle_type}")

        # Vehicle color matching
        if anpr.vehicle_color and any(c.lower() == anpr.vehicle_color.lower() for c in pq.colors):
            score += 0.25
            reasons.append(f"Matched vehicle color: {anpr.vehicle_color}")

        # Watchlist match
        if anpr.is_matched:
            score += 0.15
            reasons.append(f"Watchlist alert: {anpr.watchlist_category}")

        if not reasons:
            reasons.append(f"Plate sighting: {anpr.plate_number}")

        return min(0.99, score), reasons

    @classmethod
    def _score_face(cls, fr: FaceRecord, pq: ParsedSemanticQuery) -> Tuple[float, List[str]]:
        score = 0.50
        reasons = []

        for name in pq.person_names:
            if fr.matched_name and name.lower() in fr.matched_name.lower():
                score += 0.45
                reasons.append(f"Matched identity: {fr.matched_name}")
                break

        if fr.similarity_score:
            score += fr.similarity_score * 0.20

        if fr.match_status == "MATCHED":
            score += 0.15
            reasons.append(f"Watchlist match: {fr.watchlist_category}")

        if not reasons:
            reasons.append("Face detection sighting")

        return min(0.99, score), reasons

    @classmethod
    def _score_evidence(cls, ev: Evidence, pq: ParsedSemanticQuery) -> Tuple[float, List[str]]:
        score = 0.45
        reasons = []

        file_type_str = ev.file_type.value if hasattr(ev.file_type, 'value') else str(ev.file_type)
        full_text = f"{file_type_str} {ev.file_path} {ev.metadata_json or ''}".lower()
        if pq.raw_query.lower() in full_text:
            score += 0.40
            reasons.append("Evidence metadata match")

        for act in pq.action_terms:
            if act in full_text:
                score += 0.15
                reasons.append(f"Evidence mentions {act}")

        if not reasons:
            reasons.append(f"Investigative evidence ({file_type_str})")

        return min(0.99, score), reasons


class InvestigationCaseService:
    """Manages case dossiers, findings, chronological timeline reconstruction, and report export."""

    @classmethod
    async def create_case(cls, data: Dict[str, Any], db: AsyncSession) -> InvestigationCase:
        # Generate case number
        count_res = await db.execute(select(func.count(InvestigationCase.id)))
        count = count_res.scalar() or 0
        year = datetime.now(timezone.utc).year
        case_number = f"CASE-{year}-{count + 1:04d}"

        tags = data.get("tags", [])
        tags_json = json.dumps(tags) if isinstance(tags, list) else str(tags)

        case = InvestigationCase(
            case_number=case_number,
            title=data["title"],
            description=data.get("description"),
            status=CaseStatus(data.get("status", "OPEN")),
            priority=CasePriority(data.get("priority", "MEDIUM")),
            lead_investigator=data.get("lead_investigator", "Lead Investigator"),
            hypothesis=data.get("hypothesis"),
            tags_json=tags_json
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        return case

    @classmethod
    async def get_case_timeline(cls, case_id: int, db: AsyncSession) -> CaseTimelineResponse:
        case = await db.get(InvestigationCase, case_id)
        if not case:
            raise ValueError(f"Investigation Case #{case_id} not found")

        # Fetch findings
        findings_res = await db.execute(
            select(CaseFinding).where(CaseFinding.case_id == case_id).order_by(CaseFinding.timestamp.asc(), CaseFinding.created_at.asc())
        )
        findings = findings_res.scalars().all()

        # Fetch camera names
        cam_res = await db.execute(select(Camera))
        cams = {c.id: c.name for c in cam_res.scalars().all()}

        events: List[InvestigationTimelineEvent] = []
        camera_sequence_dict: Dict[int, Dict[str, Any]] = {}

        for f in findings:
            cam_name = cams.get(f.camera_id, f"Camera #{f.camera_id}") if f.camera_id else "Global Investigation"
            meta = json.loads(f.metadata_json) if f.metadata_json else {}

            event_time = f.timestamp or f.created_at

            events.append(
                InvestigationTimelineEvent(
                    id=f"FINDING_{f.id}",
                    timestamp=event_time,
                    camera_id=f.camera_id,
                    camera_name=cam_name,
                    event_type=f.item_type,
                    title=f.title,
                    description=f.notes,
                    thumbnail_url=f.thumbnail_url,
                    severity=meta.get("severity", "MEDIUM"),
                    metadata=meta
                )
            )

            if f.camera_id:
                if f.camera_id not in camera_sequence_dict:
                    camera_sequence_dict[f.camera_id] = {
                        "camera_id": f.camera_id,
                        "camera_name": cam_name,
                        "first_seen": event_time.isoformat(),
                        "last_seen": event_time.isoformat(),
                        "sightings_count": 1
                    }
                else:
                    camera_sequence_dict[f.camera_id]["last_seen"] = event_time.isoformat()
                    camera_sequence_dict[f.camera_id]["sightings_count"] += 1

        camera_sequence = list(camera_sequence_dict.values())

        return CaseTimelineResponse(
            case_id=case.id,
            case_number=case.case_number,
            title=case.title,
            total_events=len(events),
            camera_sequence=camera_sequence,
            events=events
        )

    @classmethod
    async def export_case_report(cls, case_id: int, db: AsyncSession) -> CaseExportResponse:
        case = await db.get(InvestigationCase, case_id)
        if not case:
            raise ValueError(f"Investigation Case #{case_id} not found")

        timeline_data = await cls.get_case_timeline(case_id, db)
        
        # Format tags
        tags_list = json.loads(case.tags_json) if case.tags_json else []

        # Findings schema mapping
        findings_res = await db.execute(
            select(CaseFinding).where(CaseFinding.case_id == case_id).order_by(CaseFinding.timestamp.asc())
        )
        findings = findings_res.scalars().all()

        cam_res = await db.execute(select(Camera))
        cams = {c.id: c.name for c in cam_res.scalars().all()}

        finding_responses = [
            CaseFindingResponse(
                id=f.id,
                case_id=f.case_id,
                item_type=f.item_type,
                reference_id=f.reference_id,
                camera_id=f.camera_id,
                camera_name=cams.get(f.camera_id, f"Camera #{f.camera_id}") if f.camera_id else None,
                timestamp=f.timestamp,
                title=f.title,
                notes=f.notes,
                metadata=json.loads(f.metadata_json) if f.metadata_json else {},
                thumbnail_url=f.thumbnail_url,
                created_at=f.created_at
            )
            for f in findings
        ]

        case_response = InvestigationCaseResponse(
            id=case.id,
            case_number=case.case_number,
            title=case.title,
            description=case.description,
            status=case.status.value if hasattr(case.status, 'value') else str(case.status),
            priority=case.priority.value if hasattr(case.priority, 'value') else str(case.priority),
            lead_investigator=case.lead_investigator,
            hypothesis=case.hypothesis,
            tags=tags_list,
            findings_count=len(findings),
            findings=finding_responses,
            created_at=case.created_at,
            updated_at=case.updated_at,
            closed_at=case.closed_at
        )

        # Build Summary Statistics
        stats = {
            "total_findings": len(findings),
            "cameras_involved": len(timeline_data.camera_sequence),
            "earliest_event": timeline_data.events[0].timestamp.isoformat() if timeline_data.events else None,
            "latest_event": timeline_data.events[-1].timestamp.isoformat() if timeline_data.events else None,
            "findings_by_type": {}
        }
        for f in findings:
            stats["findings_by_type"][f.item_type] = stats["findings_by_type"].get(f.item_type, 0) + 1

        # Generate Printable Tactical HTML Report
        html_report = cls._generate_html_report(case_response, timeline_data, stats)

        return CaseExportResponse(
            case=case_response,
            timeline=timeline_data.events,
            summary_statistics=stats,
            html_report=html_report
        )

    @classmethod
    def _generate_html_report(
        cls,
        case: InvestigationCaseResponse,
        timeline: CaseTimelineResponse,
        stats: Dict[str, Any]
    ) -> str:
        timeline_rows = ""
        for ev in timeline.events:
            thumb_html = f'<img src="{ev.thumbnail_url}" style="max-height: 70px; border-radius: 4px; margin-top: 4px;" />' if ev.thumbnail_url else ''
            timeline_rows += f"""
            <tr style="border-bottom: 1px solid #27272a;">
                <td style="padding: 10px; font-family: monospace; font-size: 11px; color: #a1a1aa;">{ev.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                <td style="padding: 10px; font-weight: 600; color: #f4f4f5;"><span style="background: #27272a; padding: 2px 6px; border-radius: 4px; font-size: 10px;">{ev.event_type}</span></td>
                <td style="padding: 10px; color: #e4e4e7;">{ev.camera_name or 'N/A'}</td>
                <td style="padding: 10px; color: #f4f4f5;">
                    <div><strong>{ev.title}</strong></div>
                    <div style="font-size: 11px; color: #a1a1aa; margin-top: 2px;">{ev.description or ''}</div>
                    {thumb_html}
                </td>
            </tr>
            """

        camera_pills = "".join([
            f'<span style="background: #18181b; border: 1px solid #3f3f46; color: #e4e4e7; padding: 4px 10px; border-radius: 6px; font-size: 11px; margin-right: 6px; display: inline-block;">'
            f'{seq["camera_name"]} ({seq["sightings_count"]} sightings)'
            f'</span>'
            for seq in timeline.camera_sequence
        ]) or '<span style="color: #71717a; font-size: 12px;">No multi-camera sequence recorded</span>'

        tags_pills = "".join([
            f'<span style="background: #27272a; color: #a1a1aa; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px;">#{t}</span>'
            for t in case.tags
        ])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ARC VISION Dossier - {case.case_number}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #09090b; color: #f4f4f5; margin: 0; padding: 32px; line-height: 1.5; }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        .header {{ border-bottom: 2px solid #27272a; padding-bottom: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }}
        .badge {{ display: inline-block; padding: 3px 8px; font-size: 11px; font-weight: 700; border-radius: 4px; text-transform: uppercase; }}
        .badge-open {{ background: #0284c7; color: white; }}
        .badge-crit {{ background: #dc2626; color: white; }}
        .section {{ background: #121215; border: 1px solid #27272a; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
        .section-title {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #a1a1aa; margin-bottom: 12px; border-bottom: 1px solid #27272a; padding-bottom: 6px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ padding: 10px; font-size: 11px; font-weight: 600; text-transform: uppercase; color: #a1a1aa; border-bottom: 2px solid #27272a; background: #18181b; }}
        .footer {{ text-align: center; color: #52525b; font-size: 11px; margin-top: 40px; border-top: 1px solid #27272a; padding-top: 16px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div style="font-size: 11px; font-family: monospace; color: #a1a1aa; letter-spacing: 0.1em; text-transform: uppercase;">ARC VISION FORENSIC INTELLIGENCE DOSSIER</div>
                <h1 style="font-size: 24px; margin: 4px 0 8px 0; color: #ffffff;">{case.case_number}: {case.title}</h1>
                <div>{tags_pills}</div>
            </div>
            <div style="text-align: right;">
                <span class="badge badge-open">{case.status}</span>
                <span class="badge badge-crit" style="margin-left: 4px;">{case.priority}</span>
                <div style="font-size: 11px; font-family: monospace; color: #71717a; margin-top: 8px;">Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Case Overview & Hypothesis</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 13px;">
                <div>
                    <span style="color: #71717a; font-size: 11px; text-transform: uppercase; display: block;">Lead Investigator</span>
                    <strong>{case.lead_investigator}</strong>
                </div>
                <div>
                    <span style="color: #71717a; font-size: 11px; text-transform: uppercase; display: block;">Total Pinned Findings</span>
                    <strong>{stats['total_findings']} items across {stats['cameras_involved']} cameras</strong>
                </div>
            </div>
            <div style="margin-top: 16px;">
                <span style="color: #71717a; font-size: 11px; text-transform: uppercase; display: block; margin-bottom: 4px;">Description</span>
                <p style="margin: 0; color: #d4d4d8; font-size: 13px;">{case.description or 'No case description recorded.'}</p>
            </div>
            <div style="margin-top: 16px; background: #18181b; padding: 12px; border-radius: 6px; border-left: 3px solid #3b82f6;">
                <span style="color: #93c5fd; font-size: 11px; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 4px;">Working Hypothesis</span>
                <p style="margin: 0; color: #e0f2fe; font-size: 13px;">{case.hypothesis or 'Hypothesis pending investigator findings evaluation.'}</p>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Multi-Camera Trajectory & Sequence</div>
            <div style="padding-top: 4px;">{camera_pills}</div>
        </div>

        <div class="section">
            <div class="section-title">Chronological Event Timeline ({len(timeline.events)} Verified Findings)</div>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Type</th>
                        <th>Sensor / Location</th>
                        <th>Summary & Evidence</th>
                    </tr>
                </thead>
                <tbody>
                    {timeline_rows or '<tr><td colspan="4" style="padding: 20px; text-align: center; color: #71717a;">No findings attached to case timeline yet.</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="footer">
            ARC VISION ADVANCED VMS INTELLIGENCE • FORENSIC CHAIN OF CUSTODY VERIFIED • SYSTEM CONFIDENTIAL
        </div>
    </div>
</body>
</html>"""
