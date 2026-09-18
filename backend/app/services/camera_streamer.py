import cv2
import time
import json
import asyncio
import threading
import queue
import logging
import concurrent.futures
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.event_bus import event_bus
from app.services.ai.detector import detector_service
from app.services.ai.tracker import MultiObjectTracker
from app.services.ai.motion_detector import MotionDetector
from app.services.ai.anpr_engine import anpr_engine
from app.services.ai.night_vision import night_vision_processor
from app.services.analytics.zone_engine import zone_engine
from app.services.analytics.behavior_engine import behavior_engine
from app.services.analytics.rule_evaluator import rule_evaluator
from app.services.analytics.incident_intelligence import incident_intelligence
from app.services.evidence_manager import evidence_manager
from app.services.recording_engine import recording_engine
from app.services.snapshot_manager import snapshot_manager
from app.services.analytics.event_engine import event_engine
from app.services.ai.perception.orchestrator import perception_orchestrator
from app.services.analytics.cross_camera.global_track_manager import global_track_manager
from app.services.ai.face.service import face_service
from app.services.ai.anpr.service import anpr_service
from app.services.ai.anpr.normalizer import normalize_indian_plate, clean_raw_plate

logger = logging.getLogger("arc_vision.streamer")

class CameraStreamer:
    def __init__(
        self,
        camera_id: int,
        camera_name: str,
        stream_url: str,
        stream_type: str = "FILE",
        target_fps: int = 25,
        zones: List[Dict[str, Any]] = None,
        tripwires: List[Dict[str, Any]] = None,
        is_night_mode: bool = True,
        anpr_enabled: bool = True
    ):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.stream_url = stream_url
        self.stream_type = stream_type
        self.target_fps = max(20, target_fps)
        self.is_night_mode = is_night_mode
        self.anpr_enabled = anpr_enabled

        self.zones = zones or []
        self.tripwires = tripwires or []
        self.rules: List[Any] = []
        self.motion_masks: List[List[Tuple[float, float]]] = []

        self.motion_detector = MotionDetector(threshold=25, min_area=400)
        self.tracker = MultiObjectTracker()
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_detections: List[Any] = []
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_jpeg_bytes: Optional[bytes] = None
        self.latest_raw_jpeg_bytes: Optional[bytes] = None
        self.latest_motion_boxes: List[List[float]] = []
        self.latest_motion_score: float = 0.0
        self._vehicle_plate_cache: Dict[int, Dict[str, Any]] = {}
        self._person_face_cache: Dict[int, Dict[str, Any]] = {}
        self._in_flight_ocr_tracks: set = set()
        self._ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"Cam{self.camera_id}_OCR")
        
        # Telemetry
        self.is_running = False
        self.status = "CONNECTING"
        self.current_fps = 0.0
        self.latency_ms = 0.0
        self.frame_count = 0
        self.drop_count = 0
        self.last_frame_time = time.time()
        self._is_inferencing = False
        
        self._thread: Optional[threading.Thread] = None
        self._ai_worker_thread: Optional[threading.Thread] = None
        self._inference_queue: queue.Queue = queue.Queue(maxsize=1)
        self._last_clip_time = 0.0
        self._lock = threading.Lock()

    def _dispatch_task(self, coro):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
            return
        except RuntimeError:
            pass

        async def _safe_runner():
            try:
                await coro
            except Exception as e:
                logger.debug(f"[Background Task] Cam #{self.camera_id} exception: {e}")
        threading.Thread(target=lambda: asyncio.run(_safe_runner()), daemon=True).start()

    def _async_write_segment(self, seg_meta: Dict[str, Any]):
        """Background thread worker to write MP4 and persist segment to database."""
        try:
            frames = seg_meta.pop("_frames", [])
            fps = seg_meta.pop("_fps", 15)
            file_path = seg_meta.pop("_file_path", None)
            if frames and file_path:
                h, w = frames[0].shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(str(file_path), fourcc, fps, (w, h))
                for f in frames:
                    out.write(f)
                out.release()
                p = Path(file_path)
                if p.exists():
                    seg_meta["file_size_bytes"] = p.stat().st_size
                    from app.services.recording_engine import compute_sha256
                    seg_meta["sha256_hash"] = compute_sha256(p)

            # Persist to database asynchronously
            self._dispatch_task(self._save_segment_task(seg_meta))
        except Exception as e:
            logger.error(f"Error async writing segment for camera #{self.camera_id}: {e}")

    async def _save_segment_task(self, seg_meta: Dict[str, Any]):
        try:
            async with AsyncSessionLocal() as session:
                await recording_engine.persist_segment(seg_meta, session)
        except Exception as e:
            logger.debug(f"Error saving segment for camera #{self.camera_id}: {e}")

    async def _save_snapshots_task(self, snaps: List[Dict[str, Any]]):
        try:
            async with AsyncSessionLocal() as session:
                await snapshot_manager.persist_snapshots(snaps, session)
        except Exception as e:
            logger.debug(f"Error saving snapshots for camera #{self.camera_id}: {e}")

    async def _ingest_cross_camera_task(self, obs_data_list: List[Dict[str, Any]]):
        async with AsyncSessionLocal() as session:
            for obs in obs_data_list:
                try:
                    await global_track_manager.ingest_observation(
                        camera_id=obs["camera_id"],
                        camera_name=obs["camera_name"],
                        local_track_id=obs["local_track_id"],
                        object_class=obs["object_class"],
                        box=obs["box"],
                        timestamp=obs.get("timestamp"),
                        duration_sec=obs.get("duration_sec", 0.0),
                        plate_number=obs.get("plate_number"),
                        face_identity_id=obs.get("face_identity_id"),
                        face_name=obs.get("face_name"),
                        sector_name=obs.get("sector_name", "Perimeter Sector"),
                        zones=obs.get("zones", []),
                        db=session
                    )
                except Exception as e:
                    logger.debug(f"Cross camera ingestion error: {e}")

    def update_config(self, zones: List[Dict[str, Any]] = None, tripwires: List[Dict[str, Any]] = None, rules: List[Any] = None, anpr_enabled: Optional[bool] = None):
        with self._lock:
            if zones is not None:
                self.zones = zones
            if tripwires is not None:
                self.tripwires = tripwires
            if rules is not None:
                self.rules = rules
            if anpr_enabled is not None:
                self.anpr_enabled = anpr_enabled

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ai_worker_thread = threading.Thread(target=self._ai_worker_loop, daemon=True)
        self._ai_worker_thread.start()
        logger.info(f"Started camera streamer #{self.camera_id} ({self.camera_name})")

    def stop(self):
        self.is_running = False
        try:
            self._inference_queue.put_nowait((None, -1))
        except Exception:
            pass
        try:
            self._ocr_executor.shutdown(wait=False)
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._ai_worker_thread and self._ai_worker_thread.is_alive():
            self._ai_worker_thread.join(timeout=1.0)
        self.status = "OFFLINE"
        logger.info(f"Stopped camera streamer #{self.camera_id}")

    def _ai_worker_loop(self):
        """Dedicated persistent background worker for AI inference."""
        while self.is_running:
            try:
                item = self._inference_queue.get(timeout=0.2)
                if item is None or item[0] is None:
                    continue
                inf_frame, frame_num = item
                self._process_ai_inference(inf_frame, frame_num)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in Cam #{self.camera_id} AI worker: {e}")

    def _open_capture(self) -> cv2.VideoCapture:
        url = str(self.stream_url or "").strip()
        
        # 1. RTSP / HTTP Stream URL
        if url.startswith(("rtsp://", "http://", "https://", "rtsps://")):
            return cv2.VideoCapture(url)

        # 2. Local device webcam index
        if url.isdigit():
            return cv2.VideoCapture(int(url))

        # 3. Direct path or resolved candidate file paths for the specific stream_url
        clean_url = url.lstrip("/\\")
        raw_p = Path(url)
        candidates = [
            raw_p,
            settings.BASE_DIR / clean_url,
            settings.DATA_DIR / clean_url,
            settings.UPLOADS_DIR / raw_p.name,
            settings.DEMO_DIR / raw_p.name,
            settings.BASE_DIR.parent / raw_p.name,
        ]

        for p in candidates:
            try:
                if p.exists() and p.is_file() and p.stat().st_size > 0:
                    cap = cv2.VideoCapture(str(p.resolve()))
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            logger.info(f"Camera #{self.camera_id} [{self.camera_name}] successfully opened video source: {p}")
                            return cap
                        cap.release()
            except Exception as e:
                logger.debug(f"Candidate {p} check failed: {e}")

        # 4. Fallback demo videos ONLY if the requested stream_url file cannot be found
        fallback_candidates = [
            settings.BASE_DIR.parent / "sample.mp4",
            settings.DEMO_DIR / "sample.mp4",
            settings.DEMO_DIR / "night_perimeter_breach.mp4",
            settings.DEMO_DIR / "checkpoint_anpr_vehicle.mp4"
        ]
        for p in fallback_candidates:
            try:
                if p.exists() and p.is_file() and p.stat().st_size > 0:
                    cap = cv2.VideoCapture(str(p.resolve()))
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            logger.info(f"Camera #{self.camera_id} [{self.camera_name}] using fallback video source: {p}")
                            return cap
                        cap.release()
            except Exception as e:
                logger.debug(f"Fallback candidate {p} check failed: {e}")

        # 5. Fallback to default demo asset generator
        try:
            ensure_demo_assets()
            default_demo = settings.DEMO_DIR / "night_perimeter_breach.mp4"
            if default_demo.exists():
                cap = cv2.VideoCapture(str(default_demo.resolve()))
                if cap.isOpened():
                    return cap
        except Exception:
            pass

        return cv2.VideoCapture(url)

    def _annotate_frame(self, frame: np.ndarray, detections: List[Any]) -> np.ndarray:
        """Renders live tactical HUD overlays, bounding boxes, and virtual fence lines."""
        overlay = frame.copy()
        h, w = frame.shape[:2]

        # Draw Zones (Crisp tactical borders)
        for z in self.zones:
            pts = z.get("points", [])
            if len(pts) >= 3:
                pixel_pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in pts], np.int32)
                color = (220, 220, 220) if z.get("zone_type") == "RESTRICTED" else (140, 140, 140)
                cv2.polylines(overlay, [pixel_pts], True, color, 2)
                lx, ly = pixel_pts[0]
                cv2.putText(overlay, f"ZONE: {z.get('name')}", (lx + 5, ly - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        # Draw Tripwires / Virtual Fences
        for tw in self.tripwires:
            start = tw["line"]["start"]
            end = tw["line"]["end"]
            p1 = (int(start[0] * w), int(start[1] * h))
            p2 = (int(end[0] * w), int(end[1] * h))
            cv2.line(overlay, p1, p2, (240, 240, 240), 2)
            cv2.circle(overlay, p1, 3, (255, 255, 255), -1)
            cv2.circle(overlay, p2, 3, (255, 255, 255), -1)
            cv2.putText(overlay, f"FENCE: {tw.get('name')}", (p1[0], p1[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        # Draw Tracked Detections (Crisp Tactical HUD with Dedicated Number Plate Target Squares)
        for det in detections:
            x1 = int(det.box[0] * w)
            y1 = int(det.box[1] * h)
            x2 = int(det.box[2] * w)
            y2 = int(det.box[3] * h)
            vw = max(1, x2 - x1)
            vh = max(1, y2 - y1)

            is_vehicle = det.class_name in ["car", "truck", "bus", "motorcycle", "vehicle", "van", "auto", "train"]
            is_matched = det.attributes.get("is_matched", False)
            plate_number = det.attributes.get("plate")

            # Vehicle & Object Bounding Box Color
            if is_matched:
                box_color = (30, 30, 240) # Alert Red for Watchlist hits
            elif is_vehicle and plate_number:
                box_color = (40, 230, 100) # Bright Neon Emerald
            elif is_vehicle:
                box_color = (255, 255, 255) # Tactical White
            else:
                box_color = (255, 255, 255)

            cv2.rectangle(overlay, (x1, y1), (x2, y2), box_color, 2)

            # Corner brackets for tactical HUD look
            b_len = max(8, int(min(vw, vh) * 0.15))
            cv2.line(overlay, (x1, y1), (x1 + b_len, y1), (255, 255, 255), 2)
            cv2.line(overlay, (x1, y1), (x1, y1 + b_len), (255, 255, 255), 2)
            cv2.line(overlay, (x2, y2), (x2 - b_len, y2), (255, 255, 255), 2)
            cv2.line(overlay, (x2, y2), (x2, y2 - b_len), (255, 255, 255), 2)
            cv2.line(overlay, (x2, y1), (x2 - b_len, y1), (255, 255, 255), 2)
            cv2.line(overlay, (x2, y1), (x2, y1 + b_len), (255, 255, 255), 2)
            cv2.line(overlay, (x1, y2), (x1 + b_len, y2), (255, 255, 255), 2)
            cv2.line(overlay, (x1, y2), (x1, y2 - b_len), (255, 255, 255), 2)

            # Top label banner
            dwell = det.attributes.get("dwell_sec", 0.0)
            tag = f"ID:{det.track_id} {det.class_name.upper()} {int(det.confidence * 100)}% | {dwell}s"
            tag_w = len(tag) * 8 + 8
            banner_top_y = max(20, y1)
            cv2.rectangle(overlay, (x1, banner_top_y - 20), (x1 + tag_w, banner_top_y), (0, 0, 0), -1)
            cv2.rectangle(overlay, (x1, banner_top_y - 20), (x1 + tag_w, banner_top_y), box_color, 1)
            cv2.putText(overlay, tag, (x1 + 4, banner_top_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

            # VEHICLE NUMBER PLATE TARGET SQUARE & TEXT HUD
            # ONLY render when a license plate is detected! Never show fake "SCANNING" box.
            if is_vehicle and plate_number:
                p_box = det.attributes.get("plate_box")
                if p_box and len(p_box) == 4:
                    px1, py1, px2, py2 = p_box
                    pl_x1 = max(x1, min(x2 - 10, x1 + int(px1)))
                    pl_y1 = max(y1, min(y2 - 5, y1 + int(py1)))
                    pl_x2 = max(pl_x1 + 25, min(x2, x1 + int(px2)))
                    pl_y2 = max(pl_y1 + 10, min(y2, y1 + int(py2)))
                else:
                    # Realistic vehicle plate location (lower-center fascia)
                    pl_x1 = int(x1 + vw * 0.22)
                    pl_x2 = int(x1 + vw * 0.78)
                    pl_y1 = int(y1 + vh * 0.65)
                    pl_y2 = int(y1 + vh * 0.88)

                # Clamp & enforce minimum dimensions for crisp rendering
                if (pl_x2 - pl_x1) < 46:
                    cx = (pl_x1 + pl_x2) // 2
                    pl_x1 = max(x1, cx - 23)
                    pl_x2 = min(x2, cx + 23)
                if (pl_y2 - pl_y1) < 16:
                    cy = (pl_y1 + pl_y2) // 2
                    pl_y1 = max(y1, cy - 8)
                    pl_y2 = min(y2, cy + 8)

                pl_color = (30, 30, 240) if is_matched else (40, 230, 100)

                # 1. Draw Target Square around Number Plate
                cv2.rectangle(overlay, (pl_x1, pl_y1), (pl_x2, pl_y2), pl_color, 2)

                # 2. Draw 4 Corner HUD Crosshair ticks on Plate Square
                c_tick = max(4, int(min(pl_x2 - pl_x1, pl_y2 - pl_y1) * 0.35))
                cv2.line(overlay, (pl_x1, pl_y1), (pl_x1 + c_tick, pl_y1), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x1, pl_y1), (pl_x1, pl_y1 + c_tick), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x2, pl_y2), (pl_x2 - c_tick, pl_y2), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x2, pl_y2), (pl_x2, pl_y2 - c_tick), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x2, pl_y1), (pl_x2 - c_tick, pl_y1), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x2, pl_y1), (pl_x2, pl_y1 + c_tick), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x1, pl_y2), (pl_x1 + c_tick, pl_y2), (255, 255, 255), 2)
                cv2.line(overlay, (pl_x1, pl_y2), (pl_x1, pl_y2 - c_tick), (255, 255, 255), 2)

                # 3. High-Contrast Plate Text Display Banner
                wl_cat = det.attributes.get("watchlist_category", "FLAGGED")
                if is_matched:
                    p_label = f"ALERT [{wl_cat}]: {plate_number}"
                else:
                    p_label = f"PLATE: {plate_number}"

                (tw, th), _ = cv2.getTextSize(p_label, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
                by = pl_y1 - 4 if pl_y1 > (th + 10) else pl_y2 + th + 12
                bx1 = max(4, pl_x1)
                bx2 = min(w - 4, bx1 + tw + 10)

                cv2.rectangle(overlay, (bx1, by - th - 6), (bx2, by + 2), (0, 0, 0), -1)
                cv2.rectangle(overlay, (bx1, by - th - 6), (bx2, by + 2), pl_color, 1)
                cv2.putText(overlay, p_label, (bx1 + 5, by - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)

            # Unique Person / Face HUD Badge
            person_uid = det.attributes.get("unique_person_id")
            face_name = det.attributes.get("face_name")
            if person_uid or face_name:
                face_tag = f"FACE: {face_name or person_uid} [{person_uid or 'ID'}]"
                f_w = len(face_tag) * 8 + 10
                cv2.rectangle(overlay, (x1, y2), (x1 + f_w, y2 + 18), (0, 0, 0), -1)
                cv2.rectangle(overlay, (x1, y2), (x1 + f_w, y2 + 18), (0, 200, 255), 1)
                cv2.putText(overlay, face_tag, (x1 + 4, y2 + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 200, 255), 1)

        # Tactical Status Watermark
        cv2.putText(overlay, f"{self.camera_name} | {self.current_fps:.1f} FPS", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return overlay

    def _run_ocr_for_track(
        self,
        track_id: int,
        vehicle_class: str,
        v_crop: np.ndarray,
        frame: np.ndarray,
        frame_num: int,
        dwell_sec: float,
        is_stationary: bool
    ):
        """Asynchronous OCR worker running in thread pool to prevent blocking YOLO & tracking."""
        try:
            v_h, v_w = v_crop.shape[:2]
            y_start = int(v_h * 0.25) if vehicle_class in ["motorcycle", "bicycle", "bike", "scooter", "motorbike"] else int(v_h * 0.30)
            plate_roi = v_crop[y_start:v_h, :]
            p_res = anpr_service.ocr_adapter.detect_and_read_from_frame(plate_roi if plate_roi.size > 0 else v_crop)
            if not p_res and plate_roi.size > 0:
                p_res = anpr_service.ocr_adapter.detect_and_read_from_frame(v_crop)
                y_start = 0

            if p_res:
                p_text = p_res.get("cleaned_text") or p_res.get("raw_text")
                raw_p = p_res.get("raw_text")
                p_box = p_res.get("box")
                p_conf = p_res.get("confidence", 0.8)
                if p_box and y_start > 0:
                    p_box = [p_box[0], p_box[1] + y_start, p_box[2], p_box[3] + y_start]

                if p_text and len(clean_raw_plate(p_text)) >= 3:
                    norm_p, _ = normalize_indian_plate(p_text)
                    if not norm_p:
                        norm_p = clean_raw_plate(p_text)

                    with self._lock:
                        existing = self._vehicle_plate_cache.get(track_id, {})
                        self._vehicle_plate_cache[track_id] = {
                            "plate": norm_p or p_text,
                            "raw_text": raw_p or p_text,
                            "plate_box": p_box,
                            "conf": p_conf,
                            "is_matched": existing.get("is_matched", False),
                            "watchlist_category": existing.get("watchlist_category"),
                            "last_ocr_time": time.time(),
                            "frame_num": frame_num
                        }

            # Dispatch ANPR DB persistence and watchlist matching asynchronously with precomputed data
            self._dispatch_task(
                anpr_service.process_vehicle(
                    camera_id=self.camera_id,
                    camera_name=self.camera_name,
                    track_id=track_id,
                    vehicle_class=vehicle_class,
                    vehicle_crop=v_crop,
                    full_frame=frame,
                    dwell_duration_sec=dwell_sec,
                    is_stationary=is_stationary,
                    precomputed_plate_data=p_res
                )
            )
        except Exception as e:
            logger.debug(f"Async OCR for Cam #{self.camera_id} track #{track_id} error: {e}")
        finally:
            with self._lock:
                self._in_flight_ocr_tracks.discard(track_id)

    def _process_ai_inference(self, frame: np.ndarray, frame_num: int):
        """Asynchronous worker for non-blocking AI detection, perception, and rule evaluation."""
        try:
            # Downscale frame for fast real-time inference (640px max)
            h_orig, w_orig = frame.shape[:2]
            if w_orig > 640:
                inf_w = 640
                inf_h = int(640 * h_orig / w_orig)
                proc_frame = cv2.resize(frame, (inf_w, inf_h))
            else:
                proc_frame = frame

            # 1. Motion detection
            has_motion, motion_score, motion_boxes, _ = self.motion_detector.detect(proc_frame, self.motion_masks)
            self.latest_motion_boxes = motion_boxes
            self.latest_motion_score = motion_score

            # 2. YOLO Object Detection & Tracking (Full-resolution high recall threshold 0.18)
            det_frame = frame
            if self.is_night_mode and (frame_num % 4 == 0):
                det_frame = night_vision_processor.enhance_low_light(det_frame)
            raw_detections = detector_service.detect(det_frame, confidence_threshold=0.18)
            tracked = self.tracker.update(raw_detections)

            has_incident_this_frame = False
            all_fired_events = []
            active_zones_map = {}
            evidence_package = {}

            # 2b. Live Face Detection & Unique Person ID Tracking (Async)
            person_trks = [{"track_id": d.track_id, "box": d.box} for d in tracked if d.class_name in ["person", "human", "pedestrian"]]
            if person_trks and (frame_num % 2 == 0):
                async def _async_face_proc(f_copy, p_trks):
                    evs = await face_service.process_frame_faces(
                        camera_id=self.camera_id,
                        camera_name=self.camera_name,
                        frame=f_copy,
                        person_tracks=p_trks
                    )
                    if evs:
                        with self._lock:
                            for ev in evs:
                                t_id = ev.get("track_id")
                                if t_id:
                                    self._person_face_cache[t_id] = {
                                        "unique_person_id": ev.get("unique_person_id"),
                                        "face_name": ev.get("identity_name"),
                                        "is_matched": ev.get("match_status") == "KNOWN"
                                    }
                self._dispatch_task(_async_face_proc(frame.copy(), person_trks))

            # 3. Spatial Rules & High-Precision ANPR License Plate Tracking for all vehicle types
            VEHICLE_TYPES = ["car", "truck", "bus", "motorcycle", "bicycle", "bike", "scooter", "motorbike", "vehicle", "van", "auto", "train"]
            for det in tracked:
                centroid = det.attributes.get("centroid", (0.5, 0.5))
                traj = det.attributes.get("trajectory", [])

                active_z = zone_engine.check_zone_occupancy(centroid, self.zones)
                active_zones_map[det.track_id] = active_z
                breaches = zone_engine.check_tripwire_crossing(traj, self.tripwires)

                # Attach cached face ID to person track
                if det.class_name in ["person", "human", "pedestrian"]:
                    cached_f = self._person_face_cache.get(det.track_id)
                    if cached_f:
                        det.attributes["unique_person_id"] = cached_f.get("unique_person_id")
                        det.attributes["face_name"] = cached_f.get("face_name")
                        if cached_f.get("is_matched"):
                            det.attributes["is_matched"] = True

                if self.anpr_enabled and det.class_name in VEHICLE_TYPES:
                    vx1, vy1 = max(0, int(det.box[0] * w_orig)), max(0, int(det.box[1] * h_orig))
                    vx2, vy2 = min(w_orig, int(det.box[2] * w_orig)), min(h_orig, int(det.box[3] * h_orig))
                    
                    # 10% padding around vehicle to capture entire bumper, grill, front/rear plates
                    pad_w = int((vx2 - vx1) * 0.10)
                    pad_h = int((vy2 - vy1) * 0.10)
                    vx1_pad = max(0, vx1 - pad_w)
                    vy1_pad = max(0, vy1 - pad_h)
                    vx2_pad = min(w_orig, vx2 + pad_w)
                    vy2_pad = min(h_orig, vy2 + pad_h)
                    
                    if vx2_pad > vx1_pad and vy2_pad > vy1_pad:
                        v_crop = frame[vy1_pad:vy2_pad, vx1_pad:vx2_pad]
                        
                        # Instantly attach cached plate attributes
                        cached_plate = self._vehicle_plate_cache.get(det.track_id)
                        if cached_plate:
                            det.attributes["plate"] = cached_plate.get("plate")
                            det.attributes["plate_raw"] = cached_plate.get("raw_text")
                            det.attributes["plate_box"] = cached_plate.get("plate_box")
                            det.attributes["plate_conf"] = cached_plate.get("conf", 0.85)
                            det.attributes["is_matched"] = cached_plate.get("is_matched", False)
                            det.attributes["watchlist_category"] = cached_plate.get("watchlist_category")

                        # Trigger asynchronous background OCR if not cached or periodic refresh (every 3s)
                        now_ts = time.time()
                        needs_ocr = (not cached_plate) or (now_ts - cached_plate.get("last_ocr_time", 0.0) > 3.0)
                        if needs_ocr and det.track_id not in self._in_flight_ocr_tracks:
                            with self._lock:
                                self._in_flight_ocr_tracks.add(det.track_id)
                            self._ocr_executor.submit(
                                self._run_ocr_for_track,
                                det.track_id,
                                det.class_name,
                                v_crop.copy(),
                                frame.copy(),
                                frame_num,
                                det.attributes.get("dwell_sec", 0.0),
                                det.attributes.get("is_stationary", False)
                            )

                fired_events = rule_evaluator.evaluate(
                    camera_id=self.camera_id,
                    rules=self.rules,
                    detection=det,
                    active_zones=active_z,
                    tripwire_breaches=breaches,
                    is_night_mode=self.is_night_mode
                )
                all_fired_events.extend(fired_events)

                if fired_events:
                    has_incident_this_frame = True
                    code = f"INC-{time.strftime('%Y')}-{self.camera_id:02d}{det.track_id:02d}"
                    snap_meta = evidence_manager.save_snapshot(self.camera_id, frame, code)
                    # Rate-limit heavy incident clip encoding (at most once every 10s per camera)
                    if (time.time() - self._last_clip_time) > 10.0:
                        self._last_clip_time = time.time()
                        threading.Thread(
                            target=evidence_manager.save_incident_clip,
                            args=(self.camera_id, code, self.target_fps),
                            daemon=True
                        ).start()
                    crop_meta = evidence_manager.save_crop(frame, det.box, crop_type=f"CROP_{det.class_name.upper()}", prefix=code)
                    evidence_package = {
                        "snapshot": snap_meta,
                        "clip": {"status": "ENCODING_ASYNC"},
                        "crop": crop_meta
                    }

            # 4. Perception Orchestrator (Fall, Weapon, Fire, Crowd)
            try:
                perception_events = perception_orchestrator.process_camera_frame(
                    camera_id=self.camera_id,
                    frame=proc_frame,
                    frame_idx=frame_num,
                    tracked_objects=tracked,
                    zones=self.zones
                )
                for pe in perception_events:
                    all_fired_events.append({
                        "event_type": pe.get("event_type", "SPECIALIZED_AI_DETECTION"),
                        "severity": pe.get("severity", "HIGH"),
                        "description": pe.get("explanation", "Specialized AI perception event detected"),
                        "details": pe,
                        "track_id": pe.get("track_id", -1)
                    })
                    has_incident_this_frame = True
            except Exception as e:
                logger.error(f"[Fault-Isolation] Perception Cam #{self.camera_id}: {e}")

            # 5. Dispatch Event Engine
            if tracked or all_fired_events:
                self._dispatch_task(
                    event_engine.process_frame_events(
                        camera_id=self.camera_id,
                        camera_name=self.camera_name,
                        tracked_detections=tracked,
                        fired_rule_events=all_fired_events,
                        active_zones_map=active_zones_map,
                        evidence_dict=evidence_package if has_incident_this_frame else None,
                        is_night_mode=self.is_night_mode
                    )
                )

            # 6. Cross-Camera Re-ID
            if tracked and (frame_num % 10 == 0):
                obs_list = []
                for det in tracked:
                    if det.class_name in ["person", "car", "truck", "bus", "motorcycle"]:
                        obs_list.append({
                            "camera_id": self.camera_id,
                            "camera_name": self.camera_name,
                            "local_track_id": det.track_id,
                            "object_class": det.class_name,
                            "box": det.box,
                            "timestamp": time.time(),
                            "duration_sec": 0.5,
                            "plate_number": det.attributes.get("plate"),
                            "face_identity_id": det.attributes.get("face_id"),
                            "face_name": det.attributes.get("face_name"),
                            "sector_name": "Perimeter Sector Alpha",
                            "zones": active_zones_map.get(det.track_id, [])
                        })
                if obs_list:
                    self._dispatch_task(self._ingest_cross_camera_task(obs_list))

            self._last_inference_time = time.time()
            with self._lock:
                self.latest_detections = tracked

        except Exception as ex:
            logger.error(f"Inference error in Cam #{self.camera_id}: {ex}")
        finally:
            self._is_inferencing = False

    def _run_loop(self):
        cap = self._open_capture()
        
        # Read video native FPS if available
        try:
            n_fps = cap.get(cv2.CAP_PROP_FPS)
            if 15.0 <= n_fps <= 60.0:
                self.target_fps = int(n_fps)
            else:
                self.target_fps = max(25, self.target_fps)
        except Exception:
            self.target_fps = max(25, self.target_fps)

        fps_timer = time.time()
        frames_in_second = 0
        frame_delay = 1.0 / max(1, self.target_fps)
        reconnect_attempts = 0
        last_reconnect_time = 0.0

        # Discover resolution & codec metadata
        try:
            self.resolution_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
            self.resolution_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        except Exception:
            self.resolution_w = 1280
            self.resolution_h = 720

        while self.is_running:
            try:
                loop_start = time.time()
                
                if not cap.isOpened():
                    self.status = "CONNECTING"
                    import random
                    backoff_delay = min(15.0, (1.5 ** min(reconnect_attempts, 6)) + random.uniform(0.1, 0.5))
                    if time.time() - last_reconnect_time > backoff_delay:
                        reconnect_attempts += 1
                        logger.info(f"Camera #{self.camera_id} [{self.camera_name}] reconnect attempt #{reconnect_attempts}...")
                        cap.release()
                        cap = self._open_capture()
                        last_reconnect_time = time.time()
                    time.sleep(0.05)
                    continue

                ret, frame = cap.read()

                if not ret or frame is None:
                    # If reached end of video file, rewind seamlessly
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret2, frame2 = cap.read()
                    if ret2 and frame2 is not None:
                        frame = frame2
                        reconnect_attempts = 0
                    else:
                        # Reopen capture instantly for continuous loop
                        cap.release()
                        cap = self._open_capture()
                        ret3, frame3 = cap.read()
                        if ret3 and frame3 is not None:
                            frame = frame3
                            reconnect_attempts = 0
                        else:
                            self.status = "CONNECTING"
                            import random
                            backoff_delay = min(15.0, (1.5 ** min(reconnect_attempts, 6)) + random.uniform(0.1, 0.5))
                            if time.time() - last_reconnect_time > backoff_delay:
                                reconnect_attempts += 1
                                cap.release()
                                cap = self._open_capture()
                                last_reconnect_time = time.time()
                            time.sleep(0.05)
                            continue

                reconnect_attempts = 0
                self.status = "ONLINE"
                self.frame_count += 1
                frames_in_second += 1
                self.last_frame_time = time.time()

                # 1. Real-time velocity extrapolation on intermediate frames for 25-30 FPS smoothness
                dt = time.time() - getattr(self, "_last_inference_time", time.time())
                if dt > 0.02 and self.tracker.tracks:
                    current_detections = self.tracker.predict_all(dt)
                else:
                    with self._lock:
                        current_detections = list(self.latest_detections)

                # Attach cached plate/face attributes
                for det in current_detections:
                    cached_p = self._vehicle_plate_cache.get(det.track_id)
                    if cached_p:
                        det.attributes["plate"] = cached_p.get("plate")
                        det.attributes["plate_box"] = cached_p.get("plate_box")
                        det.attributes["is_matched"] = cached_p.get("is_matched", False)
                        det.attributes["watchlist_category"] = cached_p.get("watchlist_category")
                    cached_f = self._person_face_cache.get(det.track_id)
                    if cached_f:
                        det.attributes["unique_person_id"] = cached_f.get("unique_person_id")
                        det.attributes["face_name"] = cached_f.get("face_name")
                        if cached_f.get("is_matched"):
                            det.attributes["is_matched"] = True

                annotated = self._annotate_frame(frame, current_detections)
                ret_ann, jpeg_ann = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 72])
                ret_raw, jpeg_raw = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 72])

                with self._lock:
                    self.latest_frame = frame
                    self.latest_annotated_frame = annotated
                    if ret_ann:
                        self.latest_jpeg_bytes = jpeg_ann.tobytes()
                    if ret_raw:
                        self.latest_raw_jpeg_bytes = jpeg_raw.tobytes()

                # 2. Buffer for recording and evidence
                evidence_manager.buffer_frame(self.camera_id, frame)

                # 3. Feed background AI worker queue
                try:
                    if self._inference_queue.empty():
                        self._inference_queue.put_nowait((frame, self.frame_count))
                except Exception:
                    pass

                # 4. Continuous Recording feed
                detected_classes = [d.class_name for d in current_detections]
                seg_meta = recording_engine.feed_frame(
                    camera_id=self.camera_id,
                    frame=frame,
                    has_objects=len(current_detections) > 0,
                    detected_classes=detected_classes,
                    motion_score=self.latest_motion_score,
                    is_incident_event=False,
                    fps=self.target_fps,
                    segment_duration=10.0
                )
                if seg_meta:
                    threading.Thread(target=self._async_write_segment, args=(seg_meta,), daemon=True).start()

                # Calculate FPS
                now = time.time()
                if now - fps_timer >= 1.0:
                    self.current_fps = round(frames_in_second / (now - fps_timer), 1)
                    frames_in_second = 0
                    fps_timer = now

                # Measure latency estimate from frame delta
                actual_delta = time.time() - loop_start
                self.latency_ms = round(actual_delta * 1000.0, 1)

                # Throttle to smooth target FPS
                elapsed = time.time() - loop_start
                sleep_time = max(0.001, frame_delay - elapsed)
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Error in Camera #{self.camera_id} loop: {e}")
                time.sleep(0.05)

        cap.release()
        self.status = "OFFLINE"

    def get_jpeg_bytes(self, annotated: bool = True) -> Optional[bytes]:
        with self._lock:
            cached = self.latest_jpeg_bytes if annotated else self.latest_raw_jpeg_bytes
            if cached is not None:
                return cached
            
            target = self.latest_annotated_frame if annotated else self.latest_frame
            if target is None:
                placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.rectangle(placeholder, (20, 20), (1260, 700), (45, 55, 75), 1)
                cv2.putText(placeholder, f"ARC VISION TACTICAL NVR | CAMERA #{self.camera_id}", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 1)
                cv2.putText(placeholder, f"{self.camera_name.upper()}", (40, 330), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.putText(placeholder, f"STREAM STATUS: {self.status} | INITIALIZING AI INGESTION...", (40, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 2)
                cv2.putText(placeholder, f"SOURCE: {self.stream_url}", (40, 415), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 160, 180), 1)
                ret, jpeg = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 80])
                return jpeg.tobytes() if ret else None
            ret, jpeg = cv2.imencode('.jpg', target, [cv2.IMWRITE_JPEG_QUALITY, 72])
            return jpeg.tobytes() if ret else None
