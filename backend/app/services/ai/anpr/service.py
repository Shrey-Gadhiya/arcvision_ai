import os
import time
import base64
import logging
import asyncio
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import cv2
import numpy as np
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.anpr import (
    ANPRRecord,
    ANPRWatchlist,
    PlateWatchlistCategory,
    WatchlistPriority,
    PlateValidationStatus
)
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.models.evidence import Evidence, EvidenceType
from app.core.event_bus import event_bus
from app.services.ai.anpr.base import (
    BasePlateDetectorAdapter,
    BasePlateOCRAdapter,
    PlateDetectionResult,
    OCRResult,
    ValidationOutcome,
    AdapterStatus
)
from app.services.ai.anpr.adapters import (
    HeuristicPlateDetectorAdapter,
    EasyOCRPlateAdapter,
    UnavailablePlateDetectorAdapter,
    UnavailableOCRAdapter
)
from app.services.ai.anpr.normalizer import normalize_indian_plate, clean_raw_plate
from app.services.ai.anpr.validators import IndianPlateValidator
from app.services.notification_service import notification_service

logger = logging.getLogger("arc_vision.anpr.service")

# Recognizable vehicle classes
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle", "vehicle"}

class PlateRecognitionService:
    """
    Production ANPR Orchestrator.
    Pipeline: Frame -> Vehicle Detection -> Vehicle Track -> Plate Detection -> Plate Crop -> OCR -> Normalization -> Validation -> Watchlist -> Event/Incident/Evidence.
    """
    def __init__(self):
        # Initialize default adapters
        self.detector_adapter: BasePlateDetectorAdapter = HeuristicPlateDetectorAdapter()
        self.ocr_adapter: BasePlateOCRAdapter = EasyOCRPlateAdapter()
        
        # Try loading OCR adapter
        self.ocr_adapter.load()
        if self.ocr_adapter.status != AdapterStatus.LOADED:
            logger.info("EasyOCR not active. Operating with heuristic plate localization & explicit unavailable OCR reporting.")

        # Camera configurations: camera_id -> config dict
        self.camera_configs: Dict[int, Dict[str, Any]] = {}
        
        # Sighting cooldown tracking: (camera_id, track_id) -> last_seen_ts, (camera_id, plate) -> last_seen_ts
        self._track_cooldown: Dict[Tuple[int, int], float] = {}
        self._plate_cooldown: Dict[Tuple[int, str], float] = {}
        self.default_cooldown_sec: float = 15.0

        # Snapshot storage directory
        self.anpr_storage_dir = os.path.join("data", "snapshots", "anpr")
        os.makedirs(self.anpr_storage_dir, exist_ok=True)

    def configure_camera(
        self,
        camera_id: int,
        enabled: bool = True,
        confidence_threshold: float = 0.45,
        validation_region: str = "INDIAN_RTO",
        cooldown_sec: float = 15.0
    ):
        self.camera_configs[camera_id] = {
            "enabled": enabled,
            "confidence_threshold": confidence_threshold,
            "validation_region": validation_region,
            "cooldown_sec": cooldown_sec
        }

    def is_camera_enabled(self, camera_id: int) -> bool:
        if camera_id in self.camera_configs:
            return self.camera_configs[camera_id].get("enabled", True)
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine_name": "ARC-VISION Production ANPR Engine",
            "detector_adapter": self.detector_adapter.name,
            "detector_status": self.detector_adapter.status.value,
            "ocr_adapter": self.ocr_adapter.name,
            "ocr_status": self.ocr_adapter.status.value,
            "ocr_details": self.ocr_adapter.last_error or "OCR Ready",
            "active_cameras_count": len(self.camera_configs),
            "total_sightings_today": 0,
            "validation_capabilities": ["INDIAN_STANDARD_RTO_36_STATES", "BHARAT_SERIES_BH", "DEFENCE_MILITARY"]
        }

    async def _save_crop_and_hash(self, img: np.ndarray, prefix: str) -> Tuple[Optional[str], Optional[str], int]:
        """Saves image to disk and calculates SHA-256 hash."""
        if img is None or img.size == 0:
            return None, None, 0
        try:
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{prefix}_{ts_str}.jpg"
            filepath = os.path.join(self.anpr_storage_dir, filename)
            cv2.imwrite(filepath, img)

            with open(filepath, "rb") as f:
                content = f.read()
                sha256 = hashlib.sha256(content).hexdigest()
                size_bytes = len(content)

            url_path = f"/static/snapshots/anpr/{filename}"
            return url_path, sha256, size_bytes
        except Exception as e:
            logger.error(f"Failed to save ANPR crop: {e}")
            return None, None, 0

    async def capture_and_detect_plate(
        self,
        image_data: Any,
        camera_id: Optional[int] = None,
        camera_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes an uploaded image or camera snapshot to detect vehicle and license plate,
        extracts characters via OCR, normalizes the plate, validates RTO format,
        checks active watchlists, saves dual snapshots, and records sighting in database.
        """
        # 1. Decode image data if base64 string
        frame = None
        if isinstance(image_data, str):
            try:
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                img_bytes = base64.b64decode(image_data)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to decode base64 image: {str(e)}",
                    "diagnostics": "Image decoding failed"
                }
        elif isinstance(image_data, np.ndarray):
            frame = image_data

        if frame is None or frame.size == 0:
            return {
                "success": False,
                "error": "Empty image provided",
                "diagnostics": "Null or zero-sized image"
            }

        cam_id = camera_id or 1
        cam_name = camera_name or f"Camera #{cam_id}"

        # 2. Run OCR & Plate Detection
        raw_text = ""
        ocr_conf = 0.0
        plate_crop = None
        plate_box = None

        if isinstance(self.ocr_adapter, EasyOCRPlateAdapter) and self.ocr_adapter.status == AdapterStatus.LOADED:
            det_res = self.ocr_adapter.detect_and_read_from_frame(frame)
            if det_res:
                raw_text = det_res.get("raw_text", "")
                ocr_conf = float(det_res.get("confidence", 0.0))
                plate_crop = det_res.get("plate_crop")
                plate_box = det_res.get("box")

        if not raw_text:
            # Fallback to detector adapter + read_plate
            plate_detections = self.detector_adapter.detect_plates(frame)
            if plate_detections:
                plate_crop = plate_detections[0].plate_crop
                ocr_res = self.ocr_adapter.read_plate(plate_crop)
                raw_text = ocr_res.raw_text
                ocr_conf = float(ocr_res.confidence)
                plate_box = ocr_res.metadata.get("box")

        if not raw_text:
            return {
                "success": False,
                "error": "No license plate or characters detected in the image",
                "diagnostics": "OCR scan found no alphanumeric vehicle registration text",
                "ocr_status": self.ocr_adapter.status.value
            }

        # 3. Normalization & Validation
        normalized_plate, norm_meta = normalize_indian_plate(raw_text)
        if not normalized_plate:
            normalized_plate = clean_raw_plate(raw_text)

        validation = IndianPlateValidator.validate(normalized_plate)
        val_status = PlateValidationStatus.VALID if validation.status == "VALID" else (
            PlateValidationStatus.UNCERTAIN if validation.status == "UNCERTAIN" else PlateValidationStatus.INVALID
        )
        final_confidence = round(float((ocr_conf + validation.confidence) / 2.0), 3)

        # 4. Check Watchlist Hotlist
        is_matched = False
        watchlist_category = None
        watchlist_priority = None
        watch_entry = None

        async with AsyncSessionLocal() as session:
            try:
                watch_res = await session.execute(
                    select(ANPRWatchlist).where(
                        ANPRWatchlist.plate_number == normalized_plate,
                        ANPRWatchlist.is_active == True
                    )
                )
                watch_entry = watch_res.scalars().first()
                if watch_entry:
                    is_matched = True
                    watchlist_category = watch_entry.category.value
                    watchlist_priority = watch_entry.priority.value
            except Exception as e:
                logger.warning(f"Watchlist lookup failed during capture: {e}")

        # 5. Save Dual/Triple Snapshots & Generate Tactical Annotated Overlay ("detect square upon")
        if plate_crop is None or plate_crop.size == 0:
            plate_crop = frame

        plate_crop_url, plate_sha, _ = await self._save_crop_and_hash(plate_crop, f"capture_plate_{normalized_plate}")
        full_frame_url, full_sha, full_size = await self._save_crop_and_hash(frame, f"capture_full_{normalized_plate}")

        # Draw target square and tactical HUD banner on annotated frame
        annotated_frame = frame.copy()
        if plate_box and len(plate_box) == 4:
            x1, y1, x2, y2 = [int(v) for v in plate_box]
            box_col = (30, 30, 220) if is_matched else (40, 220, 100) # BGR
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_col, 2)
            # Corner brackets for tactical look
            bl = max(8, int(min(x2 - x1, y2 - y1) * 0.25))
            cv2.line(annotated_frame, (x1, y1), (x1 + bl, y1), (255, 255, 255), 2)
            cv2.line(annotated_frame, (x1, y1), (x1, y1 + bl), (255, 255, 255), 2)
            cv2.line(annotated_frame, (x2, y2), (x2 - bl, y2), (255, 255, 255), 2)
            cv2.line(annotated_frame, (x2, y2), (x2, y2 - bl), (255, 255, 255), 2)
            
            # Target square banner
            tag = f"PLATE: {normalized_plate} [{int(final_confidence * 100)}%]"
            if is_matched:
                tag = f"ALERT [{watchlist_category}]: {normalized_plate}"
            t_w = len(tag) * 8 + 10
            banner_y = max(22, y1)
            cv2.rectangle(annotated_frame, (x1, banner_y - 20), (x1 + t_w, banner_y), (0, 0, 0), -1)
            cv2.rectangle(annotated_frame, (x1, banner_y - 20), (x1 + t_w, banner_y), box_col, 1)
            cv2.putText(annotated_frame, tag, (x1 + 4, banner_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        annotated_frame_url, _, _ = await self._save_crop_and_hash(annotated_frame, f"annotated_{normalized_plate}")

        # 6. Database Persistence & Evidence Creation
        async with AsyncSessionLocal() as session:
            try:
                record = ANPRRecord(
                    camera_id=cam_id,
                    track_id=101,
                    raw_text=raw_text,
                    plate_number=normalized_plate,
                    confidence=final_confidence,
                    validation_status=val_status,
                    validation_format=validation.format_name,
                    diagnostics=f"Neural OCR Capture. {validation.diagnostics}",
                    vehicle_type="vehicle",
                    is_stationary=True,
                    dwell_duration_sec=0.0,
                    is_matched=is_matched,
                    watchlist_category=watchlist_category,
                    watchlist_priority=watchlist_priority,
                    crop_path=plate_crop_url,
                    vehicle_crop_path=plate_crop_url,
                    full_frame_path=annotated_frame_url or full_frame_url,
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(record)
                await session.flush()

                # Create Evidence Record
                if full_frame_url:
                    ev = Evidence(
                        incident_id=None,
                        camera_id=cam_id,
                        file_type=EvidenceType.CROP_PLATE,
                        file_path=plate_crop_url,
                        file_size_bytes=full_size,
                        sha256_hash=plate_sha or "",
                        metadata_json=json.dumps({
                            "type": "ANPR_MANUAL_CAPTURE",
                            "plate_number": normalized_plate,
                            "raw_text": raw_text,
                            "confidence": final_confidence,
                            "is_matched": is_matched,
                            "annotated_frame": annotated_frame_url
                        })
                    )
                    session.add(ev)
                    await session.flush()
                    record.evidence_id = ev.id

                # Create Watchlist Incident if Matched
                incident_id = None
                if is_matched:
                    incident_code = f"INC-ANPR-{cam_id}-{int(time.time()) % 100000}"
                    severity = IncidentSeverity.CRITICAL if watchlist_priority in ("CRITICAL", "HIGH") else IncidentSeverity.HIGH
                    inc = Incident(
                        incident_code=incident_code,
                        title=f"Watchlist Plate Alert: {normalized_plate} ({watchlist_category})",
                        summary=f"Flagged vehicle plate {normalized_plate} [{watchlist_category}] captured. Notes: {watch_entry.notes or 'No notes'}",
                        incident_type="WATCHLIST_MATCH",
                        camera_id=cam_id,
                        track_id=101,
                        severity=severity,
                        status=IncidentStatus.DETECTED,
                        threat_score=95.0 if watchlist_priority == "CRITICAL" else 85.0,
                        location_name=cam_name,
                        tags_json=json.dumps(["ANPR", "WATCHLIST", watchlist_category, "MANUAL_CAPTURE"])
                    )
                    session.add(inc)
                    await session.flush()
                    incident_id = inc.id

                await session.commit()

                # Broadcast notification & event
                payload = {
                    "record_id": record.id,
                    "camera_id": cam_id,
                    "camera_name": cam_name,
                    "plate_number": normalized_plate,
                    "raw_text": raw_text,
                    "confidence": final_confidence,
                    "validation_status": val_status.value,
                    "validation_format": validation.format_name,
                    "is_matched": is_matched,
                    "watchlist_category": watchlist_category,
                    "watchlist_priority": watchlist_priority,
                    "crop_path": plate_crop_url,
                    "vehicle_crop_path": plate_crop_url,
                    "full_frame_path": full_frame_url,
                    "timestamp": record.timestamp.isoformat()
                }
                await event_bus.publish("anpr:plate_detected", payload)

                return {
                    "success": True,
                    "record_id": record.id,
                    "plate_number": normalized_plate,
                    "raw_text": raw_text,
                    "confidence": final_confidence,
                    "ocr_confidence": ocr_conf,
                    "validation_status": val_status.value,
                    "validation_format": validation.format_name,
                    "diagnostics": validation.diagnostics,
                    "is_matched": is_matched,
                    "watchlist_category": watchlist_category,
                    "watchlist_priority": watchlist_priority,
                    "plate_crop_url": plate_crop_url,
                    "full_frame_url": full_frame_url,
                    "annotated_frame_url": annotated_frame_url,
                    "plate_box": plate_box,
                    "error": None
                }
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in capture_and_detect_plate: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "diagnostics": "Database transaction error"
                }

    async def process_vehicle(
        self,
        camera_id: int,
        camera_name: str,
        track_id: int,
        vehicle_class: str,
        vehicle_crop: np.ndarray,
        full_frame: Optional[np.ndarray] = None,
        dwell_duration_sec: float = 0.0,
        is_stationary: bool = False,
        recording_segment_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes complete ANPR & Vehicle Intelligence flow for a vehicle sighting.
        """
        if not self.is_camera_enabled(camera_id):
            return None

        if vehicle_class.lower() not in VEHICLE_CLASSES:
            return None

        now = time.time()
        cooldown_duration = self.camera_configs.get(camera_id, {}).get("cooldown_sec", self.default_cooldown_sec)

        # 1. Check track cooldown to prevent processing identical track every frame
        if (camera_id, track_id) in self._track_cooldown:
            if now - self._track_cooldown[(camera_id, track_id)] < 3.0:
                return None

        self._track_cooldown[(camera_id, track_id)] = now

        # 2. Localize Plate & Run OCR
        raw_text = ""
        ocr_confidence = 0.0
        plate_crop = None

        if isinstance(self.ocr_adapter, EasyOCRPlateAdapter) and self.ocr_adapter.status == AdapterStatus.LOADED:
            det_res = self.ocr_adapter.detect_and_read_from_frame(vehicle_crop)
            if det_res:
                raw_text = det_res.get("raw_text", "")
                ocr_confidence = float(det_res.get("confidence", 0.0))
                plate_crop = det_res.get("plate_crop")

        if not raw_text:
            plate_detections = self.detector_adapter.detect_plates(vehicle_crop)
            if not plate_detections:
                return None

            best_plate_det = plate_detections[0]
            plate_crop = best_plate_det.plate_crop
            ocr_result: OCRResult = self.ocr_adapter.read_plate(plate_crop)
            raw_text = ocr_result.raw_text.strip()
            ocr_confidence = float(ocr_result.confidence)

        # If OCR engine is unavailable or detected nothing, do NOT invent fake plates
        if not raw_text:
            return None

        # 4. Normalization & Position-Aware Character Corrections
        normalized_plate, norm_meta = normalize_indian_plate(raw_text)
        if not normalized_plate:
            normalized_plate = clean_raw_plate(raw_text)
        if not normalized_plate:
            return None

        # 5. Check plate-level cooldown
        if (camera_id, normalized_plate) in self._plate_cooldown:
            if now - self._plate_cooldown[(camera_id, normalized_plate)] < cooldown_duration:
                return None

        self._plate_cooldown[(camera_id, normalized_plate)] = now

        # 6. Format Validation (Indian RTO / Bharat Series / Military)
        validation = IndianPlateValidator.validate(normalized_plate)
        val_status = PlateValidationStatus.VALID if validation.status == "VALID" else (
            PlateValidationStatus.UNCERTAIN if validation.status == "UNCERTAIN" else PlateValidationStatus.INVALID
        )

        final_confidence = round(float((ocr_confidence + validation.confidence) / 2.0), 3)

        # 7. Media Snapshot & Crop Persistence with SHA-256 Hashes
        if plate_crop is None or plate_crop.size == 0:
            plate_crop = vehicle_crop

        plate_crop_url, plate_sha, _ = await self._save_crop_and_hash(plate_crop, f"cam{camera_id}_trk{track_id}_plate")
        veh_crop_url, veh_sha, _ = await self._save_crop_and_hash(vehicle_crop, f"cam{camera_id}_trk{track_id}_veh")
        full_frame_url, full_sha, full_size = (None, None, 0)
        if full_frame is not None:
            full_frame_url, full_sha, full_size = await self._save_crop_and_hash(full_frame, f"cam{camera_id}_full")

        # 8. Database Persistence & Watchlist Matching
        async with AsyncSessionLocal() as session:
            try:
                # Check Watchlist Match
                watch_res = await session.execute(
                    select(ANPRWatchlist).where(
                        ANPRWatchlist.plate_number == normalized_plate,
                        ANPRWatchlist.is_active == True
                    )
                )
                watch_entry = watch_res.scalars().first()

                is_matched = watch_entry is not None
                watchlist_category = watch_entry.category.value if watch_entry else None
                watchlist_priority = watch_entry.priority.value if watch_entry else None

                # Create ANPR Record
                record = ANPRRecord(
                    camera_id=camera_id,
                    track_id=track_id,
                    raw_text=raw_text,
                    plate_number=normalized_plate,
                    confidence=final_confidence,
                    validation_status=val_status,
                    validation_format=validation.format_name,
                    diagnostics=validation.diagnostics,
                    vehicle_type=vehicle_class,
                    is_stationary=is_stationary,
                    dwell_duration_sec=dwell_duration_sec,
                    is_matched=is_matched,
                    watchlist_category=watchlist_category,
                    watchlist_priority=watchlist_priority,
                    crop_path=plate_crop_url,
                    vehicle_crop_path=veh_crop_url,
                    full_frame_path=full_frame_url,
                    recording_segment_id=recording_segment_id,
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(record)
                await session.flush() # obtain record.id

                # 9. Create Evidence Record if matched or high confidence
                evidence_record_id = None
                if full_frame_url and (is_matched or final_confidence >= 0.75):
                    ev = Evidence(
                        incident_id=None,
                        camera_id=camera_id,
                        file_type=EvidenceType.SNAPSHOT,
                        file_path=full_frame_url,
                        file_size_bytes=full_size,
                        sha256_hash=full_sha or "",
                        metadata_json=json.dumps({
                            "type": "ANPR_SIGHTING",
                            "plate_number": normalized_plate,
                            "raw_text": raw_text,
                            "confidence": final_confidence,
                            "is_matched": is_matched,
                            "track_id": track_id,
                            "vehicle_class": vehicle_class
                        })
                    )
                    session.add(ev)
                    await session.flush()
                    record.evidence_id = ev.id
                    evidence_record_id = ev.id

                # 10. Watchlist Match Incident Generation
                if is_matched:
                    incident_code = f"INC-ANPR-{camera_id}-{int(time.time()) % 100000}"
                    severity = IncidentSeverity.CRITICAL if watchlist_priority in ("CRITICAL", "HIGH") else IncidentSeverity.HIGH

                    inc = Incident(
                        incident_code=incident_code,
                        title=f"Watchlist Plate Alert: {normalized_plate} ({watchlist_category})",
                        summary=f"Flagged vehicle plate {normalized_plate} [{watchlist_category}] detected on {camera_name} (Track #{track_id}). Notes: {watch_entry.notes or 'No notes'}",
                        incident_type="WATCHLIST_MATCH",
                        camera_id=camera_id,
                        track_id=track_id,
                        severity=severity,
                        status=IncidentStatus.DETECTED,
                        threat_score=95.0 if watchlist_priority == "CRITICAL" else 85.0,
                        location_name=camera_name,
                        tags_json=json.dumps(["ANPR", "WATCHLIST", watchlist_category, vehicle_class])
                    )
                    session.add(inc)
                    await session.flush()

                    if evidence_record_id:
                        # Link evidence to incident
                        ev_res = await session.execute(select(Evidence).where(Evidence.id == evidence_record_id))
                        ev_item = ev_res.scalars().first()
                        if ev_item:
                            ev_item.incident_id = inc.id

                    await session.commit()

                    # Broadcast Watchlist Alert
                    alert_payload = {
                        "incident_id": inc.id,
                        "incident_code": incident_code,
                        "title": inc.title,
                        "summary": inc.summary,
                        "camera_id": camera_id,
                        "camera_name": camera_name,
                        "plate_number": normalized_plate,
                        "category": watchlist_category,
                        "priority": watchlist_priority,
                        "crop_url": plate_crop_url,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await event_bus.publish("anpr:watchlist_match", alert_payload)
                    asyncio.create_task(notification_service.dispatch_incident_notification(alert_payload))
                else:
                    await session.commit()

                # Broadcast General Plate Event
                plate_event_payload = {
                    "record_id": record.id,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "track_id": track_id,
                    "plate_number": normalized_plate,
                    "raw_text": raw_text,
                    "confidence": final_confidence,
                    "validation_status": val_status.value,
                    "vehicle_class": vehicle_class,
                    "is_matched": is_matched,
                    "crop_url": plate_crop_url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await event_bus.publish("anpr:plate_detected", plate_event_payload)

                return plate_event_payload

            except Exception as e:
                await session.rollback()
                logger.error(f"Error in PlateRecognitionService.process_vehicle: {e}")
                return None

# Singleton instance
anpr_service = PlateRecognitionService()
