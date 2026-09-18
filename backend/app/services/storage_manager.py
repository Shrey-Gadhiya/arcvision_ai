import os
import shutil
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.camera import Camera
from app.models.recording import RecordingSegment, SegmentType
from app.models.snapshot import TrackedSnapshot
from app.models.evidence import Evidence

logger = logging.getLogger("arc_vision.storage_manager")

class StorageManager:
    def __init__(self):
        self.data_dir = settings.DATA_DIR
        self.recordings_dir = settings.RECORDINGS_DIR
        self.snapshots_dir = settings.SNAPSHOTS_DIR
        self.evidence_dir = settings.EVIDENCE_DIR

    def _get_dir_size_and_count(self, path: Path) -> tuple[int, int]:
        total_size = 0
        file_count = 0
        if not path.exists():
            return (0, 0)
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    pass
        return (total_size, file_count)

    async def get_storage_telemetry(self, session: AsyncSession) -> Dict[str, Any]:
        """Calculates global and per-camera storage breakdown with disk capacity, DB size, and retention stats."""
        # Disk system metrics
        try:
            total_disk, used_disk, free_disk = shutil.disk_usage(self.data_dir)
            disk_pct = round((used_disk / total_disk) * 100, 1)
        except Exception:
            total_disk, used_disk, free_disk, disk_pct = (100 * 1024**3, 10 * 1024**3, 90 * 1024**3, 10.0)

        rec_size, rec_count = self._get_dir_size_and_count(self.recordings_dir)
        snap_size, snap_count = self._get_dir_size_and_count(self.snapshots_dir)
        evi_size, evi_count = self._get_dir_size_and_count(self.evidence_dir)

        # Measure SQLite DB size
        db_path = self.data_dir / "arc_vision.db"
        db_size = db_path.stat().st_size if db_path.exists() else 0

        # Query oldest and newest recording segments
        oldest_res = await session.execute(
            select(func.min(RecordingSegment.start_time), func.max(RecordingSegment.end_time))
        )
        oldest_row = oldest_res.first()
        oldest_rec = oldest_row[0].isoformat() if oldest_row and oldest_row[0] else None
        newest_rec = oldest_row[1].isoformat() if oldest_row and oldest_row[1] else None

        # Query protected segments stats
        prot_res = await session.execute(
            select(func.count(RecordingSegment.id), func.sum(RecordingSegment.file_size_bytes)).where(
                RecordingSegment.is_protected == True
            )
        )
        prot_row = prot_res.first()
        prot_count = prot_row[0] or 0
        prot_bytes = prot_row[1] or 0

        # Storage Warning status
        warning_level = "NORMAL"
        warning_msg = "Storage operational within configured limits."
        if disk_pct >= 90.0:
            warning_level = "CRITICAL"
            warning_msg = f"CRITICAL: Storage capacity at {disk_pct}%. Pruning immediately required!"
        elif disk_pct >= 80.0:
            warning_level = "WARNING"
            warning_msg = f"WARNING: Storage capacity reaching threshold at {disk_pct}%."

        # Per-camera metrics from database
        result = await session.execute(select(Camera))
        cameras = result.scalars().all()
        
        per_camera = []
        for cam in cameras:
            # Query recordings for this camera
            cam_dir = self.recordings_dir / f"cam_{cam.id}"
            cam_rec_size, cam_rec_count = self._get_dir_size_and_count(cam_dir)

            cam_snap_dir = self.snapshots_dir / f"cam_{cam.id}"
            cam_snap_size, cam_snap_count = self._get_dir_size_and_count(cam_snap_dir)

            per_camera.append({
                "camera_id": cam.id,
                "camera_name": cam.name,
                "group_name": cam.group_name,
                "recording_mode": cam.recording_mode.value,
                "retention_days": cam.retention_days,
                "retention_events_days": cam.retention_events_days,
                "recording_bytes": cam_rec_size,
                "recording_count": cam_rec_count,
                "snapshot_bytes": cam_snap_size,
                "snapshot_count": cam_snap_count,
                "total_bytes": cam_rec_size + cam_snap_size
            })

        return {
            "disk_total_bytes": total_disk,
            "disk_used_bytes": used_disk,
            "disk_free_bytes": free_disk,
            "disk_used_percent": disk_pct,
            "arc_vision_total_bytes": rec_size + snap_size + evi_size + db_size,
            "categories": {
                "recordings": {"bytes": rec_size, "count": rec_count},
                "snapshots": {"bytes": snap_size, "count": snap_count},
                "evidence": {"bytes": evi_size, "count": evi_count},
                "database": {"bytes": db_size, "count": 1}
            },
            "protected_evidence": {
                "count": prot_count,
                "bytes": prot_bytes
            },
            "oldest_recording_time": oldest_rec,
            "newest_recording_time": newest_rec,
            "warning_level": warning_level,
            "warning_message": warning_msg,
            "per_camera": per_camera
        }

    async def enforce_retention(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Prunes expired continuous and event recording segments and snapshots based on
        per-camera retention policies.
        """
        now = datetime.now(timezone.utc)
        result = await session.execute(select(Camera))
        cameras = result.scalars().all()

        pruned_segments = 0
        freed_bytes = 0

        for cam in cameras:
            cont_cutoff = now - timedelta(days=cam.retention_days)
            event_cutoff = now - timedelta(days=cam.retention_events_days)

            # Query expired continuous/motion segments that are not protected
            stmt = select(RecordingSegment).where(
                and_(
                    RecordingSegment.camera_id == cam.id,
                    RecordingSegment.is_protected == False,
                    RecordingSegment.segment_type != SegmentType.EVENT,
                    RecordingSegment.end_time < cont_cutoff
                )
            )
            res = await session.execute(stmt)
            expired_cont = res.scalars().all()

            # Query expired event segments that are not protected
            event_stmt = select(RecordingSegment).where(
                and_(
                    RecordingSegment.camera_id == cam.id,
                    RecordingSegment.is_protected == False,
                    RecordingSegment.segment_type == SegmentType.EVENT,
                    RecordingSegment.end_time < event_cutoff
                )
            )
            res_event = await session.execute(event_stmt)
            expired_event = res_event.scalars().all()

            to_delete = expired_cont + expired_event
            for seg in to_delete:
                # Remove file from disk
                try:
                    rel_p = seg.file_path.lstrip("/recordings/")
                    full_p = self.recordings_dir / rel_p
                    if full_p.exists():
                        freed_bytes += full_p.stat().st_size
                        full_p.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete recording file {seg.file_path}: {e}")

                await session.delete(seg)
                pruned_segments += 1

        await session.commit()
        logger.info(f"Retention enforcement completed: pruned {pruned_segments} segments, freed {freed_bytes / (1024*1024):.2f} MB")
        return {
            "pruned_segments": pruned_segments,
            "freed_bytes": freed_bytes,
            "timestamp": now.isoformat()
        }

storage_manager = StorageManager()
