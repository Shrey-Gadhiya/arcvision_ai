import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.snapshot import TrackedSnapshot
from app.models.camera import Camera
from app.models.user import User
from app.models.audit import AuditLog
from app.api.v1.auth import get_current_user
from app.services.stream_manager import stream_manager
from app.services.snapshot_manager import snapshot_manager
from app.services.analytics.cross_camera.global_track_manager import global_track_manager
from app.core.event_bus import event_bus

router = APIRouter(prefix="/snapshots", tags=["Tracked Object Snapshots"])

@router.get("/")
async def list_snapshots(
    camera_id: Optional[int] = None,
    object_class: Optional[str] = None,
    min_confidence: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Queries tracked object best-frame snapshots with flexible categorization."""
    stmt = select(TrackedSnapshot).order_by(desc(TrackedSnapshot.timestamp))

    filters = []
    if camera_id is not None:
        filters.append(TrackedSnapshot.camera_id == camera_id)
    if object_class and object_class.upper() != "ALL":
        cls_lower = object_class.lower()
        if cls_lower in ["vehicle", "vehicles"]:
            filters.append(TrackedSnapshot.object_class.in_(["car", "truck", "bus", "motorcycle", "bicycle", "bike", "van", "auto"]))
        elif cls_lower in ["car", "cars"]:
            filters.append(TrackedSnapshot.object_class.in_(["car", "van", "auto", "vehicle"]))
        elif cls_lower in ["motorcycle", "motorcycles", "bike", "bikes"]:
            filters.append(TrackedSnapshot.object_class.in_(["motorcycle", "bike", "bicycle", "scooter", "motorbike"]))
        elif cls_lower in ["truck", "trucks", "heavy", "bus"]:
            filters.append(TrackedSnapshot.object_class.in_(["truck", "bus", "train"]))
        elif cls_lower in ["person", "persons", "pedestrian"]:
            filters.append(TrackedSnapshot.object_class.in_(["person", "human", "pedestrian"]))
        elif cls_lower in ["other", "others"]:
            filters.append(~TrackedSnapshot.object_class.in_(["person", "human", "pedestrian", "car", "van", "auto", "vehicle", "motorcycle", "bike", "bicycle", "scooter", "motorbike", "truck", "bus", "train"]))
        else:
            filters.append(TrackedSnapshot.object_class == cls_lower)

    if min_confidence is not None:
        filters.append(TrackedSnapshot.confidence >= min_confidence)
    if start_time:
        try:
            s_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            filters.append(TrackedSnapshot.timestamp >= s_dt)
        except ValueError:
            pass
    if end_time:
        try:
            e_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            filters.append(TrackedSnapshot.timestamp <= e_dt)
        except ValueError:
            pass

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    snaps = result.scalars().all()

    # Category counts summary across all active objects
    count_stmt = select(TrackedSnapshot.object_class, func.count(TrackedSnapshot.id)).group_by(TrackedSnapshot.object_class)
    if camera_id is not None:
        count_stmt = count_stmt.where(TrackedSnapshot.camera_id == camera_id)
    c_res = await db.execute(count_stmt)
    raw_counts = dict(c_res.all())

    category_summary = {
        "all": sum(raw_counts.values()),
        "person": sum(v for k, v in raw_counts.items() if k in ["person", "human", "pedestrian"]),
        "car": sum(v for k, v in raw_counts.items() if k in ["car", "van", "auto", "vehicle"]),
        "motorcycle": sum(v for k, v in raw_counts.items() if k in ["motorcycle", "bike", "bicycle", "scooter", "motorbike"]),
        "truck": sum(v for k, v in raw_counts.items() if k in ["truck", "bus", "train"]),
        "other": sum(v for k, v in raw_counts.items() if k not in ["person", "human", "pedestrian", "car", "van", "auto", "vehicle", "motorcycle", "bike", "bicycle", "scooter", "motorbike", "truck", "bus", "train"])
    }

    output = []
    for s in snaps:
        box = []
        if s.box_json:
            try:
                box = json.loads(s.box_json)
            except Exception:
                box = []

        output.append({
            "id": s.id,
            "camera_id": s.camera_id,
            "track_id": s.track_id,
            "object_class": s.object_class,
            "confidence": round(s.confidence, 3),
            "clean_image_path": s.clean_image_path,
            "annotated_image_path": s.annotated_image_path,
            "crop_image_path": s.crop_image_path,
            "box": box,
            "quality_score": round(s.quality_score, 3),
            "timestamp": s.timestamp.isoformat()
        })

    return {
        "count": len(output),
        "limit": limit,
        "offset": offset,
        "categories": category_summary,
        "snapshots": output
    }

@router.get("/{snapshot_id}")
async def get_snapshot(
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns details of a single tracked object snapshot."""
    stmt = select(TrackedSnapshot).where(TrackedSnapshot.id == snapshot_id)
    res = await db.execute(stmt)
    snap = res.scalar_one_or_none()
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    box = []
    if snap.box_json:
        try:
            box = json.loads(snap.box_json)
        except Exception:
            box = []

    return {
        "id": snap.id,
        "camera_id": snap.camera_id,
        "track_id": snap.track_id,
        "object_class": snap.object_class,
        "confidence": round(snap.confidence, 3),
        "clean_image_path": snap.clean_image_path,
        "annotated_image_path": snap.annotated_image_path,
        "crop_image_path": snap.crop_image_path,
        "box": box,
        "quality_score": round(snap.quality_score, 3),
        "timestamp": snap.timestamp.isoformat()
    }

@router.get("/recent/feed")
async def get_recent_snapshot_feed(
    camera_id: Optional[int] = None,
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns high-priority recent snapshots formatted for the Review / Activity Stream.
    Joins camera name for instant operational context.
    """
    stmt = select(TrackedSnapshot, Camera.name.label("camera_name")).join(
        Camera, TrackedSnapshot.camera_id == Camera.id, isouter=True
    ).order_by(desc(TrackedSnapshot.timestamp))

    if camera_id:
        stmt = stmt.where(TrackedSnapshot.camera_id == camera_id)

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    feed = []
    for snap, cam_name in rows:
        feed.append({
            "id": snap.id,
            "camera_id": snap.camera_id,
            "camera_name": cam_name or f"Camera {snap.camera_id}",
            "track_id": snap.track_id,
            "object_class": snap.object_class,
            "confidence": round(snap.confidence, 3),
            "clean_image_path": snap.clean_image_path,
            "annotated_image_path": snap.annotated_image_path,
            "crop_image_path": snap.crop_image_path,
            "timestamp": snap.timestamp.isoformat()
        })
    return {"feed": feed}

@router.post("/clear-all")
async def clear_all_tracked_objects(
    camera_id: Optional[int] = None,
    delete_snapshots: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tactical Purge: Flushes in-memory tracking IDs, Kalman states, and visual bounding boxes
    across active camera streamers, flushes candidate tracks, clears global tracks,
    and removes tracked object snapshots from both forensic database AND disk storage.
    """
    streamers_reset = stream_manager.clear_all_tracked_objects(camera_id)
    snapshot_manager.clear_all_tracks(camera_id)
    global_track_manager.clear_active_tracks()

    deleted_count = 0
    if delete_snapshots:
        # Delete image files from disk
        try:
            if camera_id is not None:
                cam_snap_dir = Path(settings.SNAPSHOTS_DIR) / f"cam_{camera_id}"
                if cam_snap_dir.exists():
                    shutil.rmtree(cam_snap_dir, ignore_errors=True)
            else:
                for item in os.listdir(settings.SNAPSHOTS_DIR):
                    p = Path(settings.SNAPSHOTS_DIR) / item
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    elif p.is_file():
                        try:
                            p.unlink()
                        except Exception:
                            pass
        except Exception:
            pass

        # Delete database records
        try:
            del_stmt = delete(TrackedSnapshot)
            if camera_id is not None:
                del_stmt = del_stmt.where(TrackedSnapshot.camera_id == camera_id)
            res = await db.execute(del_stmt)
            deleted_count = res.rowcount if hasattr(res, "rowcount") and res.rowcount > 0 else 0
            await db.commit()
        except Exception:
            await db.rollback()
            try:
                if camera_id is not None:
                    await db.execute(text("DELETE FROM tracked_snapshots WHERE camera_id = :cid"), {"cid": camera_id})
                else:
                    await db.execute(text("DELETE FROM tracked_snapshots"))
                await db.commit()
            except Exception:
                await db.rollback()

    # Log audit trail for security accountability
    try:
        audit = AuditLog(
            username=current_user.username,
            user_role=current_user.role.value,
            action="PURGE_TRACKED_OBJECTS",
            resource_type="TRACKER",
            resource_id=str(camera_id) if camera_id else "ALL_CAMERAS",
            details_json=json.dumps({
                "streamers_reset": streamers_reset,
                "deleted_snapshots": deleted_count,
                "camera_id": camera_id,
                "status": "SUCCESS"
            })
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass

    # Publish real-time event to all connected UI clients via WebSocket
    try:
        await event_bus.publish("tracked_objects:cleared", {
            "camera_id": camera_id,
            "purged_by": current_user.username,
            "streamers_reset": streamers_reset,
            "deleted_snapshots": deleted_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception:
        pass

    return {
        "status": "SUCCESS",
        "message": f"Successfully purged all tracked objects{' for camera #' + str(camera_id) if camera_id else ' across all cameras'}.",
        "streamers_reset": streamers_reset,
        "deleted_snapshots": deleted_count,
        "purged_by": current_user.username
    }

