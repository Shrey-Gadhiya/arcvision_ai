import re
import json
import time
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.camera import Camera, CameraStatus, StreamType
from app.models.zone import Zone, Tripwire
from app.models.incident import Incident
from app.models.event import DetectionEvent, RuleEvent
from app.models.evidence import Evidence
from app.models.recording import RecordingSegment
from app.models.snapshot import TrackedSnapshot
from app.models.anpr import ANPRRecord
from app.models.face import FaceRecord
from app.models.audit import AuditLog
from app.schemas.all_schemas import CameraResponse, CameraCreate, CameraUpdate
from app.services.stream_manager import stream_manager
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/cameras", tags=["Cameras"])

@router.get("/", response_model=List[CameraResponse])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).order_by(Camera.id))
    cameras = result.scalars().all()
    
    # Sync runtime telemetry from stream_manager
    for cam in cameras:
        streamer = stream_manager.get_streamer(cam.id)
        if streamer:
            cam.status = CameraStatus(streamer.status) if streamer.status in CameraStatus.__members__ else CameraStatus.ONLINE
            cam.current_fps = streamer.current_fps
        else:
            cam.status = CameraStatus.OFFLINE
            cam.current_fps = 0.0

    return cameras

@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalars().first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    streamer = stream_manager.get_streamer(cam.id)
    if streamer:
        cam.status = CameraStatus(streamer.status) if streamer.status in CameraStatus.__members__ else CameraStatus.ONLINE
        cam.current_fps = streamer.current_fps
    return cam

@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    data: CameraCreate,
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(Camera).where(Camera.name == data.name))
    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Camera with name '{data.name}' already exists. Please choose a unique name."
        )

    cam = Camera(**data.model_dump())
    db.add(cam)
    await db.commit()
    await db.refresh(cam)

    # Start live streamer worker
    stream_manager.start_streamer(
        camera_id=cam.id,
        camera_name=cam.name,
        stream_url=cam.rtsp_url,
        stream_type=cam.stream_type.value,
        target_fps=cam.target_fps,
        is_night_mode=bool(cam.night_mode_enabled),
        anpr_enabled=bool(cam.anpr_enabled)
    )

    try:
        audit = AuditLog(
            username="admin",
            user_role="ADMIN",
            action="CREATE_CAMERA",
            resource_type="CAMERA",
            resource_id=str(cam.id),
            details_json=json.dumps({"name": cam.name, "stream_type": cam.stream_type.value, "anpr_enabled": cam.anpr_enabled})
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass
    return cam

@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    data: CameraUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalars().first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(cam, key, val)

    await db.commit()
    await db.refresh(cam)

    # If stream or AI settings changed, reload streamer or update config
    if "rtsp_url" in update_dict or "stream_type" in update_dict or "target_fps" in update_dict:
        stream_manager.start_streamer(
            camera_id=cam.id,
            camera_name=cam.name,
            stream_url=cam.rtsp_url,
            stream_type=cam.stream_type.value,
            target_fps=cam.target_fps,
            is_night_mode=bool(cam.night_mode_enabled),
            anpr_enabled=bool(cam.anpr_enabled)
        )
    else:
        streamer = stream_manager.get_streamer(cam.id)
        if streamer:
            streamer.update_config(anpr_enabled=bool(cam.anpr_enabled))

    return cam

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalars().first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Stop the live streamer first
    stream_manager.stop_streamer(camera_id)

    # Explicitly delete all child records safely
    for model in [
        ANPRRecord, FaceRecord, RecordingSegment, TrackedSnapshot,
        Evidence, RuleEvent, DetectionEvent, Zone, Tripwire, Incident
    ]:
        try:
            await db.execute(sa_delete(model).where(model.camera_id == camera_id))
        except Exception:
            pass

    try:
        await db.delete(cam)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Fallback raw delete
        from sqlalchemy import text
        for tbl in ["anpr_records", "face_records", "recording_segments", "tracked_snapshots",
                    "evidence", "rule_events", "detection_events", "zones", "tripwires", "incidents"]:
            try:
                await db.execute(text(f"DELETE FROM {tbl} WHERE camera_id = :cid"), {"cid": camera_id})
            except Exception:
                pass
        await db.execute(text("DELETE FROM cameras WHERE id = :cid"), {"cid": camera_id})
        await db.commit()

    return None

@router.post("/{camera_id}/restart")
async def restart_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalars().first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    stream_manager.start_streamer(
        camera_id=cam.id,
        camera_name=cam.name,
        stream_url=cam.rtsp_url,
        stream_type=cam.stream_type.value,
        target_fps=cam.target_fps,
        is_night_mode=bool(cam.night_mode_enabled),
        anpr_enabled=bool(cam.anpr_enabled)
    )
    return {"status": "RESTARTED", "camera_id": camera_id}

@router.post("/upload-video")
async def upload_camera_video(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """
    Uploads an MP4 / video file to serve as a custom CCTV camera feed source.
    Streams directly to disk to handle large video files efficiently.
    """
    actual_file = file
    if actual_file is None:
        try:
            form = await request.form()
            for key in ["file", "video", "upload", "media"]:
                if key in form:
                    actual_file = form[key]
                    break
            if actual_file is None and len(form) > 0:
                actual_file = list(form.values())[0]
        except Exception:
            pass

    if actual_file is None or not hasattr(actual_file, "filename") or not actual_file.filename:
        raise HTTPException(status_code=400, detail="No video file provided in multipart upload ('file' field required).")

    raw_name = actual_file.filename or "video.mp4"
    ext = Path(raw_name).suffix.lower()
    allowed_exts = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".flv", ".3gp", ".wmv", ".mpeg", ".mpg"]
    if ext not in allowed_exts:
        ext = ".mp4"

    clean_basename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(raw_name).stem)[:50]
    timestamp = int(time.time())
    safe_name = f"video_{timestamp}_{clean_basename}{ext}"
    
    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target_path = uploads_dir / safe_name

    try:
        with open(target_path, "wb") as buffer:
            if hasattr(actual_file, "file") and actual_file.file:
                shutil.copyfileobj(actual_file.file, buffer)
            elif hasattr(actual_file, "read"):
                chunk = await actual_file.read(1024 * 1024)
                while chunk:
                    buffer.write(chunk)
                    chunk = await actual_file.read(1024 * 1024)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write video file: {str(e)}")
    finally:
        if hasattr(actual_file, "close"):
            try:
                await actual_file.close()
            except Exception:
                pass

    rel_path = f"data/uploads/{safe_name}"
    return {
        "status": "SUCCESS",
        "filename": safe_name,
        "file_path": str(target_path),
        "relative_path": rel_path,
        "url": f"/uploads/{safe_name}"
    }
