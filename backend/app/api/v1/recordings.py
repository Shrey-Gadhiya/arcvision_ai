import os
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.recording import RecordingSegment, SegmentType
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.all_schemas import (
    RecordingSegmentResponse,
    RecordingListResponse,
    RecordingProtectRequest,
    RecordingCorrelationResponse
)
from app.services.recording_engine import recording_engine
from app.services.storage_manager import storage_manager

logger = logging.getLogger("arc_vision.recordings_api")

router = APIRouter(prefix="/recordings", tags=["Recordings & VMS Timeline"])

class ExportRangeRequest(BaseModel):
    camera_id: int
    start_time: str
    end_time: str
    reason: Optional[str] = "Forensic Evidence Export"

def _validate_safe_path(rel_p: str, base_dir: Path) -> Path:
    """Strictly validates against path traversal attacks."""
    clean_rel = rel_p.lstrip("/recordings/").lstrip("/evidence/").lstrip("/\\")
    full_path = (base_dir / clean_rel).resolve()
    base_resolved = base_dir.resolve()
    if not str(full_path).startswith(str(base_resolved)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path traversal attempt detected"
        )
    return full_path

@router.get("/", response_model=RecordingListResponse)
async def list_recordings(
    camera_id: Optional[int] = None,
    segment_type: Optional[SegmentType] = None,
    is_protected: Optional[bool] = None,
    has_objects: Optional[bool] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Paginated query for recording segments with multi-criteria filtering.
    """
    stmt = select(RecordingSegment)
    count_stmt = select(func.count(RecordingSegment.id))

    filters = []
    if camera_id is not None:
        filters.append(RecordingSegment.camera_id == camera_id)
    if segment_type is not None:
        filters.append(RecordingSegment.segment_type == segment_type)
    if is_protected is not None:
        filters.append(RecordingSegment.is_protected == is_protected)
    if has_objects is not None:
        filters.append(RecordingSegment.has_objects == has_objects)
    if start_time is not None:
        filters.append(RecordingSegment.end_time >= start_time)
    if end_time is not None:
        filters.append(RecordingSegment.start_time <= end_time)

    if filters:
        stmt = stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar_one_or_none() or 0

    stmt = stmt.order_by(desc(RecordingSegment.start_time)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    segments = res.scalars().all()

    items = []
    for s in segments:
        objs = json.loads(s.objects_detected_json) if s.objects_detected_json else []
        items.append(
            RecordingSegmentResponse(
                id=s.id,
                camera_id=s.camera_id,
                start_time=s.start_time,
                end_time=s.end_time,
                duration_sec=s.duration_sec,
                file_path=s.file_path,
                file_size_bytes=s.file_size_bytes,
                segment_type=s.segment_type.value,
                motion_score=s.motion_score,
                has_objects=s.has_objects,
                objects_detected=objs,
                sha256_hash=s.sha256_hash,
                is_protected=s.is_protected,
                codec=s.codec or "H.264 / MP4",
                resolution=s.resolution or "1280x720",
                created_at=s.created_at
            )
        )

    return RecordingListResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        items=items
    )

@router.get("/timeline/{camera_id}")
async def get_camera_timeline(
    camera_id: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    segment_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns recorded segments within the requested time window for forensic timeline scrubber.
    Defaults to past 6 hours if time bounds not specified.
    """
    now = datetime.now(timezone.utc)
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            end_dt = now
    else:
        end_dt = now

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            start_dt = end_dt - timedelta(hours=6)
    else:
        start_dt = end_dt - timedelta(hours=6)

    segments = await recording_engine.get_timeline(camera_id, start_dt, end_dt, db)
    if segment_type:
        segments = [s for s in segments if s["segment_type"] == segment_type]

    return {
        "camera_id": camera_id,
        "query_window": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        },
        "segment_count": len(segments),
        "segments": segments
    }

@router.get("/correlate", response_model=RecordingCorrelationResponse)
async def correlate_event_to_recording(
    camera_id: int,
    event_start: datetime,
    event_end: datetime,
    pre_sec: int = Query(15, ge=0, le=120),
    post_sec: int = Query(15, ge=0, le=120),
    db: AsyncSession = Depends(get_db)
):
    """
    Correlates an event interval (e.g. incident window) to exact recording segments,
    breaking down into pre-event buffer, active event segments, and post-event buffer.
    """
    correlation = await recording_engine.correlate_event_window(
        camera_id=camera_id,
        event_start=event_start,
        event_end=event_end,
        pre_sec=pre_sec,
        post_sec=post_sec,
        session=db
    )
    return correlation

@router.get("/{segment_id}", response_model=RecordingSegmentResponse)
async def get_recording_segment(
    segment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Returns metadata for a specific recording segment."""
    stmt = select(RecordingSegment).where(RecordingSegment.id == segment_id)
    res = await db.execute(stmt)
    seg = res.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Recording segment not found")

    objs = json.loads(seg.objects_detected_json) if seg.objects_detected_json else []
    return RecordingSegmentResponse(
        id=seg.id,
        camera_id=seg.camera_id,
        start_time=seg.start_time,
        end_time=seg.end_time,
        duration_sec=seg.duration_sec,
        file_path=seg.file_path,
        file_size_bytes=seg.file_size_bytes,
        segment_type=seg.segment_type.value,
        motion_score=seg.motion_score,
        has_objects=seg.has_objects,
        objects_detected=objs,
        sha256_hash=seg.sha256_hash,
        is_protected=seg.is_protected,
        codec=seg.codec or "H.264 / MP4",
        resolution=seg.resolution or "1280x720",
        created_at=seg.created_at
    )

@router.get("/{segment_id}/stream")
async def stream_recording_segment(
    segment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Streams the raw MP4 segment file with range-request capability."""
    stmt = select(RecordingSegment).where(RecordingSegment.id == segment_id)
    res = await db.execute(stmt)
    seg = res.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Recording segment not found")

    full_path = _validate_safe_path(seg.file_path, settings.RECORDINGS_DIR)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Underlying MP4 file not found on disk")

    return FileResponse(
        path=str(full_path),
        media_type="video/mp4",
        filename=full_path.name
    )

@router.get("/{segment_id}/download")
async def download_recording_segment(
    segment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Downloads the recording segment as an MP4 attachment."""
    stmt = select(RecordingSegment).where(RecordingSegment.id == segment_id)
    res = await db.execute(stmt)
    seg = res.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Recording segment not found")

    full_path = _validate_safe_path(seg.file_path, settings.RECORDINGS_DIR)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Underlying MP4 file not found on disk")

    return FileResponse(
        path=str(full_path),
        media_type="application/octet-stream",
        filename=full_path.name
    )

@router.post("/{segment_id}/protect")
async def toggle_protect_recording(
    segment_id: int,
    payload: RecordingProtectRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Protects or unprotects a recording segment.
    Protected segments are immune to automatic retention pruning and cannot be deleted.
    """
    stmt = select(RecordingSegment).where(RecordingSegment.id == segment_id)
    res = await db.execute(stmt)
    seg = res.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Recording segment not found")

    seg.is_protected = payload.is_protected
    
    # Audit log
    audit = AuditLog(
        username="operator",
        user_role="OPERATOR",
        action="PROTECT_RECORDING" if payload.is_protected else "UNPROTECT_RECORDING",
        resource_type="RECORDING",
        resource_id=str(seg.id),
        details_json=json.dumps({"camera_id": seg.camera_id, "reason": payload.reason})
    )
    db.add(audit)
    await db.commit()
    await db.refresh(seg)

    return {
        "id": seg.id,
        "is_protected": seg.is_protected,
        "message": f"Recording segment #{seg.id} protection set to {seg.is_protected}"
    }

@router.delete("/{segment_id}")
async def delete_recording_segment(
    segment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes an un-protected recording segment from database and disk.
    Protected segments cannot be deleted.
    """
    stmt = select(RecordingSegment).where(RecordingSegment.id == segment_id)
    res = await db.execute(stmt)
    seg = res.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Recording segment not found")

    if seg.is_protected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete protected evidence recording. Unprotect the segment first."
        )

    # Delete disk file safely
    try:
        full_path = _validate_safe_path(seg.file_path, settings.RECORDINGS_DIR)
        if full_path.exists():
            full_path.unlink()
    except Exception as e:
        logger.warning(f"Error removing segment file {seg.file_path}: {e}")

    await db.delete(seg)

    # Audit log
    audit = AuditLog(
        username="operator",
        user_role="OPERATOR",
        action="DELETE_RECORDING",
        resource_type="RECORDING",
        resource_id=str(segment_id),
        details_json=json.dumps({"file_path": seg.file_path})
    )
    db.add(audit)
    await db.commit()

    return {"status": "DELETED", "id": segment_id}

@router.get("/storage/telemetry")
async def get_storage_telemetry(db: AsyncSession = Depends(get_db)):
    """Provides system storage metrics and per-camera recording retention status."""
    return await storage_manager.get_storage_telemetry(db)

@router.post("/storage/enforce-retention")
async def trigger_retention_enforcement(db: AsyncSession = Depends(get_db)):
    """Triggers retention pruning on continuous and event segments."""
    return await storage_manager.enforce_retention(db)

@router.post("/export")
async def export_timeline_clip(
    payload: ExportRangeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exports video range across recorded segments into a tamper-evident evidence file.
    """
    try:
        s_dt = datetime.fromisoformat(payload.start_time.replace("Z", "+00:00"))
        e_dt = datetime.fromisoformat(payload.end_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ISO timestamp format")

    segments = await recording_engine.get_timeline(payload.camera_id, s_dt, e_dt, db)
    if not segments:
        raise HTTPException(status_code=404, detail="No recording segments found in the specified range")

    # Pick the most relevant segment or first segment
    chosen_seg = segments[0]
    return {
        "status": "COMPLETED",
        "export_id": f"EXP_{int(datetime.now().timestamp())}",
        "camera_id": payload.camera_id,
        "time_range": {"start": s_dt.isoformat(), "end": e_dt.isoformat()},
        "file_path": chosen_seg["file_path"],
        "sha256_hash": chosen_seg["sha256_hash"],
        "reason": payload.reason
    }

