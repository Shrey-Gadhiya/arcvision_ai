import os
import cv2
import time
import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.recording import RecordingSegment, SegmentType
from app.models.camera import Camera, CameraRecordingMode

logger = logging.getLogger("arc_vision.recording_engine")

def compute_sha256(file_path: Path | str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

class CameraSegmentBuffer:
    """
    Buffers frames for a single camera and flushes standard segments (e.g. 10s)
    to disk and SQLite recording_segments table.
    """
    def __init__(self, camera_id: int, segment_duration_sec: float = 10.0, fps: int = 15):
        self.camera_id = camera_id
        self.segment_duration_sec = segment_duration_sec
        self.fps = fps
        self.recordings_dir = settings.RECORDINGS_DIR
        
        self.frames: List[np.ndarray] = []
        self.segment_start_time: Optional[float] = None
        self.has_objects: bool = False
        self.detected_classes: set = set()
        self.max_motion_score: float = 0.0
        self.has_incident_event: bool = False

        self._lock = threading.Lock()

    def add_frame(
        self,
        frame: np.ndarray,
        has_objects: bool = False,
        detected_classes: List[str] = None,
        motion_score: float = 0.0,
        is_incident_event: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Appends frame. If segment duration reached, finalizes and returns segment metadata.
        """
        now = time.time()
        with self._lock:
            if self.segment_start_time is None:
                self.segment_start_time = now

            # Downscale frame for segment buffer (1920px max) to prevent memory exhaustion on 4K streams
            h, w = frame.shape[:2]
            if w > 1920:
                scale_w = 1920
                scale_h = int(1920 * h / w)
                rec_frame = cv2.resize(frame, (scale_w, scale_h))
            else:
                rec_frame = frame.copy()

            self.frames.append(rec_frame)
            if has_objects:
                self.has_objects = True
            if detected_classes:
                self.detected_classes.update(detected_classes)
            if motion_score > self.max_motion_score:
                self.max_motion_score = motion_score
            if is_incident_event:
                self.has_incident_event = True

            elapsed = now - self.segment_start_time
            if elapsed >= self.segment_duration_sec and len(self.frames) >= 5:
                # Flush segment
                segment_payload = self._flush_segment(now)
                return segment_payload

        return None

    def _flush_segment(self, end_epoch: float) -> Optional[Dict[str, Any]]:
        """Prepares buffered frames for async MP4 segment writing and resets buffer."""
        start_epoch = self.segment_start_time or end_epoch
        duration = round(end_epoch - start_epoch, 2)
        frames_to_write = list(self.frames)
        classes_detected = list(self.detected_classes)
        has_objs = self.has_objects
        motion = round(self.max_motion_score, 3)
        is_event = self.has_incident_event

        # Reset buffer immediately
        self.frames = []
        self.segment_start_time = end_epoch
        self.has_objects = False
        self.detected_classes = set()
        self.max_motion_score = 0.0
        self.has_incident_event = False

        if not frames_to_write:
            return None

        # Determine segment type
        if is_event:
            seg_type = SegmentType.EVENT
        elif motion > 0.15 or has_objs:
            seg_type = SegmentType.MOTION
        else:
            seg_type = SegmentType.CONTINUOUS

        # Prepare directory: data/recordings/cam_{id}/YYYYMMDD/
        date_str = datetime.fromtimestamp(start_epoch, tz=timezone.utc).strftime("%Y%m%d")
        cam_dir = self.recordings_dir / f"cam_{self.camera_id}" / date_str
        cam_dir.mkdir(parents=True, exist_ok=True)

        filename = f"seg_{int(start_epoch)}_{int(end_epoch)}.mp4"
        file_path = cam_dir / filename
        rel_path = f"/recordings/cam_{self.camera_id}/{date_str}/{filename}"

        # Write MP4
        first_frame = frames_to_write[0]
        h, w = first_frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(file_path), fourcc, self.fps, (w, h))
        for f in frames_to_write:
            out.write(f)
        out.release()

        file_size = file_path.stat().st_size if file_path.exists() else 0
        sha_hash = compute_sha256(file_path) if file_path.exists() else ""

        start_dt = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end_epoch, tz=timezone.utc)

        return {
            "camera_id": self.camera_id,
            "start_time": start_dt,
            "end_time": end_dt,
            "duration_sec": duration,
            "file_path": rel_path,
            "absolute_path": str(file_path),
            "file_size_bytes": file_size,
            "segment_type": seg_type,
            "motion_score": motion,
            "has_objects": has_objs,
            "objects_detected_json": json.dumps(classes_detected),
            "sha256_hash": sha_hash,
            "codec": "H.264 / MP4",
            "resolution": f"{w}x{h}",
            "is_protected": False
        }

class RecordingEngine:
    def __init__(self):
        self.camera_buffers: Dict[int, CameraSegmentBuffer] = {}
        self._lock = threading.Lock()

    def feed_frame(
        self,
        camera_id: int,
        frame: np.ndarray,
        has_objects: bool = False,
        detected_classes: List[str] = None,
        motion_score: float = 0.0,
        is_incident_event: bool = False,
        fps: int = 15,
        segment_duration: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Feeds frame to the camera segment recorder.
        Returns segment payload if a segment was just completed and written.
        """
        with self._lock:
            if camera_id not in self.camera_buffers:
                self.camera_buffers[camera_id] = CameraSegmentBuffer(
                    camera_id=camera_id,
                    segment_duration_sec=segment_duration,
                    fps=fps
                )
            buf = self.camera_buffers[camera_id]

        segment_meta = buf.add_frame(
            frame=frame,
            has_objects=has_objects,
            detected_classes=detected_classes,
            motion_score=motion_score,
            is_incident_event=is_incident_event
        )
        return segment_meta

    def remove_camera(self, camera_id: int):
        """Cleans up in-memory buffer when camera is stopped or decommissioned."""
        with self._lock:
            if camera_id in self.camera_buffers:
                del self.camera_buffers[camera_id]

    async def persist_segment(self, segment_meta: Dict[str, Any], session: AsyncSession) -> Optional[RecordingSegment]:
        """Asynchronously writes the finished recording segment record to database."""
        if not segment_meta:
            return None
        
        cam_id = segment_meta.get("camera_id")
        if cam_id is not None:
            try:
                cam_check = await session.execute(select(Camera.id).where(Camera.id == cam_id))
                if not cam_check.scalar_one_or_none():
                    logger.debug(f"Skipping recording segment persistence: Camera #{cam_id} no longer exists.")
                    return None
            except Exception:
                return None

        seg = RecordingSegment(
            camera_id=segment_meta["camera_id"],
            start_time=segment_meta["start_time"],
            end_time=segment_meta["end_time"],
            duration_sec=segment_meta["duration_sec"],
            file_path=segment_meta["file_path"],
            file_size_bytes=segment_meta["file_size_bytes"],
            segment_type=segment_meta["segment_type"],
            motion_score=segment_meta["motion_score"],
            has_objects=segment_meta["has_objects"],
            objects_detected_json=segment_meta["objects_detected_json"],
            sha256_hash=segment_meta["sha256_hash"],
            is_protected=segment_meta.get("is_protected", False),
            codec=segment_meta.get("codec", "H.264 / MP4"),
            resolution=segment_meta.get("resolution", "1280x720")
        )
        try:
            session.add(seg)
            await session.commit()
            await session.refresh(seg)
            logger.info(f"Recorded new {seg.segment_type.value} segment for Camera #{seg.camera_id}: {seg.duration_sec}s ({seg.file_path})")
            return seg
        except Exception as e:
            await session.rollback()
            logger.warning(f"Could not persist recording segment for Camera #{cam_id}: {e}")
            return None

    async def get_timeline(
        self,
        camera_id: int,
        start_time: datetime,
        end_time: datetime,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Fetches all recording segments for camera between start_time and end_time,
        optimized for multi-tier timeline visualization.
        """
        stmt = select(RecordingSegment).where(
            and_(
                RecordingSegment.camera_id == camera_id,
                RecordingSegment.end_time >= start_time,
                RecordingSegment.start_time <= end_time
            )
        ).order_by(RecordingSegment.start_time.asc())

        result = await session.execute(stmt)
        records = result.scalars().all()

        output = []
        for r in records:
            output.append({
                "id": r.id,
                "camera_id": r.camera_id,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "duration_sec": r.duration_sec,
                "file_path": r.file_path,
                "file_size_bytes": r.file_size_bytes,
                "segment_type": r.segment_type.value,
                "motion_score": r.motion_score,
                "has_objects": r.has_objects,
                "objects_detected": json.loads(r.objects_detected_json) if r.objects_detected_json else [],
                "sha256_hash": r.sha256_hash,
                "is_protected": r.is_protected,
                "codec": r.codec,
                "resolution": r.resolution,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        return output

    async def correlate_event_window(
        self,
        camera_id: int,
        event_start: datetime,
        event_end: datetime,
        pre_sec: int = 15,
        post_sec: int = 15,
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Correlates an event interval (e.g., incident detection window) to the exact recording
        segments spanning [event_start - pre_sec, event_end + post_sec].
        Categorizes segments into pre-event, primary event period, and post-event.
        """
        from datetime import timedelta
        window_start = event_start - timedelta(seconds=pre_sec)
        window_end = event_end + timedelta(seconds=post_sec)

        stmt = select(RecordingSegment).where(
            and_(
                RecordingSegment.camera_id == camera_id,
                RecordingSegment.end_time >= window_start,
                RecordingSegment.start_time <= window_end
            )
        ).order_by(RecordingSegment.start_time.asc())

        result = await session.execute(stmt)
        records = result.scalars().all()

        pre_event_seg = None
        event_segs = []
        post_event_seg = None

        for r in records:
            seg_dict = {
                "id": r.id,
                "camera_id": r.camera_id,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "duration_sec": r.duration_sec,
                "file_path": r.file_path,
                "file_size_bytes": r.file_size_bytes,
                "segment_type": r.segment_type.value,
                "motion_score": r.motion_score,
                "has_objects": r.has_objects,
                "objects_detected": json.loads(r.objects_detected_json) if r.objects_detected_json else [],
                "sha256_hash": r.sha256_hash,
                "is_protected": r.is_protected,
                "codec": r.codec,
                "resolution": r.resolution,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }

            if r.end_time <= event_start:
                pre_event_seg = seg_dict
            elif r.start_time >= event_end:
                if not post_event_seg:
                    post_event_seg = seg_dict
            else:
                event_segs.append(seg_dict)

        all_mapped = [
            {
                "id": r.id,
                "camera_id": r.camera_id,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "duration_sec": r.duration_sec,
                "file_path": r.file_path,
                "file_size_bytes": r.file_size_bytes,
                "segment_type": r.segment_type.value,
                "motion_score": r.motion_score,
                "has_objects": r.has_objects,
                "objects_detected": json.loads(r.objects_detected_json) if r.objects_detected_json else [],
                "sha256_hash": r.sha256_hash,
                "is_protected": r.is_protected,
                "codec": r.codec,
                "resolution": r.resolution,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]

        return {
            "camera_id": camera_id,
            "query_window": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
                "event_start": event_start.isoformat(),
                "event_end": event_end.isoformat(),
                "pre_sec": str(pre_sec),
                "post_sec": str(post_sec)
            },
            "total_segments": len(records),
            "segments": all_mapped,
            "pre_event_segment": pre_event_seg,
            "event_segments": event_segs,
            "post_event_segment": post_event_seg
        }

recording_engine = RecordingEngine()

