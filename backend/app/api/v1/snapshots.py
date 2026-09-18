import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc
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
    """Queries tracked object best-frame snapshots."""
    stmt = select(TrackedSnapshot).order_by(desc(TrackedSnapshot.timestamp))

    filters = []
    if camera_id is not None:
        filters.append(TrackedSnapshot.camera_id == camera_id)
    if object_class:
        filters.append(TrackedSnapshot.object_class == object_class.lower())
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
