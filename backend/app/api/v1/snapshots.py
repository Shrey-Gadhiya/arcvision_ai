import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.snapshot import TrackedSnapshot
from app.models.camera import Camera

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
    db: AsyncSession = Depends(get_db)
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
async def get_snapshot(snapshot_id: int, db: AsyncSession = Depends(get_db)):
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
