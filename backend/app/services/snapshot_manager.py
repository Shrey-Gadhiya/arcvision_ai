import cv2
import time
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.snapshot import TrackedSnapshot
from app.models.camera import Camera

logger = logging.getLogger("arc_vision.snapshot_manager")

class TrackState:
    def __init__(self, track_id: int, camera_id: int, object_class: str):
        self.track_id = track_id
        self.camera_id = camera_id
        self.object_class = object_class
        self.best_score: float = -1.0
        self.best_confidence: float = 0.0
        self.best_clean_frame: Optional[np.ndarray] = None
        self.best_annotated_frame: Optional[np.ndarray] = None
        self.best_box: List[float] = [0, 0, 0, 0] # normalized [x1, y1, x2, y2]
        self.last_seen: float = time.time()
        self.persisted: bool = False
        self.snapshot_id: Optional[int] = None

class SnapshotManager:
    def __init__(self):
        self.snapshots_dir = settings.SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        # camera_id -> { track_id: TrackState }
        self.camera_tracks: Dict[int, Dict[int, TrackState]] = {}

    def _calculate_quality_score(self, frame: np.ndarray, box: List[float], confidence: float) -> float:
        """
        Calculates representative frame score based on:
        - Detection confidence (0-1)
        - Object box resolution / pixel area
        - Edge sharpness / Laplacian variance
        """
        h, w = frame.shape[:2]
        x1 = max(0, int(box[0] * w))
        y1 = max(0, int(box[1] * h))
        x2 = min(w, int(box[2] * w))
        y2 = min(h, int(box[3] * h))

        if x2 <= x1 or y2 <= y1:
            return 0.0

        box_w = x2 - x1
        box_h = y2 - y1
        area_ratio = (box_w * box_h) / max(1.0, float(w * h))
        
        # Calculate sharpness on gray crop
        crop = frame[y1:y2, x1:x2]
        try:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Normalize sharpness roughly (0 to 1000 -> 0 to 1)
            norm_sharpness = min(1.0, sharpness / 500.0)
        except Exception:
            norm_sharpness = 0.5

        # Weighted quality formula (Frigate-class best frame selector)
        score = (confidence * 0.45) + (min(1.0, area_ratio * 15.0) * 0.35) + (norm_sharpness * 0.20)
        return float(score)

    def process_frame_detections(
        self,
        camera_id: int,
        clean_frame: np.ndarray,
        annotated_frame: np.ndarray,
        tracked_detections: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluates current detections for each tracked object.
        Returns list of new or improved snapshot payloads to persist.
        """
        if camera_id not in self.camera_tracks:
            self.camera_tracks[camera_id] = {}

        now = time.time()
        tracks_map = self.camera_tracks[camera_id]
        new_or_improved: List[Dict[str, Any]] = []

        for det in tracked_detections:
            track_id = getattr(det, "track_id", None)
            if track_id is None or track_id < 0:
                continue

            obj_class = getattr(det, "class_name", "object")
            conf = getattr(det, "confidence", 0.5)
            box = getattr(det, "box", [0, 0, 0, 0])

            if track_id not in tracks_map:
                tracks_map[track_id] = TrackState(track_id, camera_id, obj_class)

            state = tracks_map[track_id]
            state.last_seen = now

            score = self._calculate_quality_score(clean_frame, box, conf)
            # Threshold improvement check: must be at least 8% better than previous or first frame
            if score > state.best_score * 1.08 or state.best_score < 0:
                state.best_score = score
                state.best_confidence = conf
                state.best_clean_frame = clean_frame.copy()
                state.best_annotated_frame = annotated_frame.copy()
                state.best_box = list(box)

                # Generate files
                date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
                target_dir = self.snapshots_dir / f"cam_{camera_id}" / date_str
                target_dir.mkdir(parents=True, exist_ok=True)

                ts_suffix = f"{int(now)}_{track_id}"
                clean_name = f"clean_{obj_class}_{ts_suffix}.jpg"
                annot_name = f"annot_{obj_class}_{ts_suffix}.jpg"
                crop_name = f"crop_{obj_class}_{ts_suffix}.jpg"

                clean_path = target_dir / clean_name
                annot_path = target_dir / annot_name
                crop_path = target_dir / crop_name

                # Write clean
                cv2.imwrite(str(clean_path), state.best_clean_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                # Write annotated
                cv2.imwrite(str(annot_path), state.best_annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                
                # Write crop with contextual margin so full person/vehicle is visible
                h, w = clean_frame.shape[:2]
                cx1 = max(0, int(box[0] * w))
                cy1 = max(0, int(box[1] * h))
                cx2 = min(w, int(box[2] * w))
                cy2 = min(h, int(box[3] * h))
                bw = cx2 - cx1
                bh = cy2 - cy1
                pad_x = int(bw * 0.12)
                pad_y = int(bh * 0.12)
                crop_x1 = max(0, cx1 - pad_x)
                crop_y1 = max(0, cy1 - pad_y)
                crop_x2 = min(w, cx2 + pad_x)
                crop_y2 = min(h, cy2 + pad_y)
                if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                    crop = clean_frame[crop_y1:crop_y2, crop_x1:crop_x2]
                    cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
                else:
                    cv2.imwrite(str(crop_path), clean_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

                payload = {
                    "camera_id": camera_id,
                    "track_id": track_id,
                    "object_class": obj_class,
                    "confidence": conf,
                    "clean_image_path": f"/snapshots/cam_{camera_id}/{date_str}/{clean_name}",
                    "annotated_image_path": f"/snapshots/cam_{camera_id}/{date_str}/{annot_name}",
                    "crop_image_path": f"/snapshots/cam_{camera_id}/{date_str}/{crop_name}",
                    "box_json": json.dumps(box),
                    "quality_score": score,
                    "timestamp": datetime.now(timezone.utc)
                }
                new_or_improved.append(payload)

        # Cleanup stale tracks inactive for > 30 seconds
        stale_ids = [t_id for t_id, s in tracks_map.items() if now - s.last_seen > 30.0]
        for t_id in stale_ids:
            del tracks_map[t_id]

        return new_or_improved

    async def persist_snapshots(self, snapshots: List[Dict[str, Any]], session: AsyncSession):
        """Persists snapshot records to database asynchronously."""
        if not snapshots:
            return
        
        # Verify camera existence before attempting insert
        cam_id = snapshots[0].get("camera_id") if snapshots else None
        if cam_id is not None:
            try:
                cam_check = await session.execute(select(Camera.id).where(Camera.id == cam_id))
                if not cam_check.scalar_one_or_none():
                    logger.debug(f"Skipping snapshots persistence: Camera #{cam_id} no longer exists.")
                    return
            except Exception:
                return

        try:
            for snap_data in snapshots:
                record = TrackedSnapshot(
                    camera_id=snap_data["camera_id"],
                    track_id=snap_data["track_id"],
                    object_class=snap_data["object_class"],
                    confidence=snap_data["confidence"],
                    clean_image_path=snap_data["clean_image_path"],
                    annotated_image_path=snap_data["annotated_image_path"],
                    crop_image_path=snap_data["crop_image_path"],
                    box_json=snap_data["box_json"],
                    quality_score=snap_data["quality_score"],
                    timestamp=snap_data["timestamp"]
                )
                session.add(record)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning(f"Could not persist snapshots: {e}")

snapshot_manager = SnapshotManager()
