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
    base_name = data.name.strip() if data.name and data.name.strip() else f"CAM-{int(time.time()) % 10000}"
    unique_name = base_name
    counter = 1
    while True:
        existing = await db.execute(select(Camera).where(Camera.name == unique_name))
        if not existing.scalars().first():
            break
        counter += 1
        unique_name = f"{base_name} ({counter})"

    cam_dict = data.model_dump()
    cam_dict["name"] = unique_name
    if not cam_dict.get("rtsp_url"):
        cam_dict["rtsp_url"] = cam_dict.get("detect_stream_url") or "sample.mp4"

    cam = Camera(**cam_dict)
    db.add(cam)
    await db.commit()
    await db.refresh(cam)

    # Start live streamer worker
    try:
        stream_type_val = cam.stream_type.value if hasattr(cam.stream_type, 'value') else str(cam.stream_type)
        stream_manager.start_streamer(
            camera_id=cam.id,
            camera_name=cam.name,
            stream_url=cam.rtsp_url,
            stream_type=stream_type_val,
            target_fps=cam.target_fps,
            is_night_mode=bool(cam.night_mode_enabled),
            anpr_enabled=bool(cam.anpr_enabled)
        )
    except Exception as e:
        pass

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

@router.post("/fetch-video-url")
async def fetch_video_from_url(request: Request):
    """
    Directly downloads a video from a remote URL onto the high-speed cloud host (10 Gbps),
    bypassing slow local upload tunnels in ~1-2 seconds.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    url = (data.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid video URL. Must start with http:// or https://")

    try:
        import urllib.request
        timestamp = int(time.time())
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(url.split("?")[0]).name)[:40]
        if not clean_name.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".webm")):
            clean_name += ".mp4"
        
        safe_name = f"cloud_{timestamp}_{clean_name}"
        uploads_dir = Path(settings.UPLOADS_DIR)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        target_path = uploads_dir / safe_name

        req = urllib.request.Request(url, headers={"User-Agent": "ARC-VISION-NVR/2.0"})
        with urllib.request.urlopen(req, timeout=45) as resp, open(target_path, "wb") as out:
            shutil.copyfileobj(resp, out, length=1024 * 1024)

        rel_path = f"data/uploads/{safe_name}"
        return {
            "status": "SUCCESS",
            "filename": safe_name,
            "file_path": str(target_path),
            "relative_path": rel_path,
            "url": f"/uploads/{safe_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download video from URL: {str(e)}")

@router.post("/upload-video")
async def upload_camera_video(
    request: Request,
    file: Optional[UploadFile] = None,
    video: Optional[UploadFile] = None,
    upload: Optional[UploadFile] = None
):
    """
    Uploads an MP4 / video file to serve as a custom CCTV camera feed source.
    Streams directly to disk with 2MB chunk buffer for high-speed uploads.
    """
    actual_file = file or video or upload
    if actual_file is None:
        try:
            form = await request.form()
            for key in ["file", "video", "upload", "media"]:
                if key in form and hasattr(form[key], "filename"):
                    actual_file = form[key]
                    break
            if actual_file is None:
                for v in form.values():
                    if hasattr(v, "filename") and v.filename:
                        actual_file = v
                        break
        except Exception:
            pass

    # If still None, handle direct binary body stream
    if actual_file is None or not hasattr(actual_file, "filename") or not actual_file.filename:
        try:
            body = await request.body()
            if body and len(body) > 100:
                timestamp = int(time.time())
                safe_name = f"video_{timestamp}_upload.mp4"
                uploads_dir = Path(settings.UPLOADS_DIR)
                uploads_dir.mkdir(parents=True, exist_ok=True)
                target_path = uploads_dir / safe_name
                with open(target_path, "wb") as f:
                    f.write(body)
                rel_path = f"data/uploads/{safe_name}"
                return {
                    "status": "SUCCESS",
                    "filename": safe_name,
                    "file_path": str(target_path),
                    "relative_path": rel_path,
                    "url": f"/uploads/{safe_name}"
                }
        except Exception:
            pass
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
                shutil.copyfileobj(actual_file.file, buffer, length=2 * 1024 * 1024)
            elif hasattr(actual_file, "read"):
                chunk = await actual_file.read(2 * 1024 * 1024)
                while chunk:
                    buffer.write(chunk)
                    chunk = await actual_file.read(2 * 1024 * 1024)
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

@router.post("/upload-chunk")
async def upload_camera_video_chunk(
    request: Request,
    file: Optional[UploadFile] = None
):
    """
    High-reliability chunked upload endpoint.
    Accepts 512KB - 1MB binary chunks and appends them sequentially to prevent
    reverse-proxy tunnel timeouts, HTTP payload size limits, or socket drops.
    """
    query_params = request.query_params
    upload_id = query_params.get("upload_id") or request.headers.get("X-Upload-ID")
    chunk_index = query_params.get("chunk_index")
    total_chunks = query_params.get("total_chunks")
    filename = query_params.get("filename")

    chunk_bytes = b""
    if file is not None:
        chunk_bytes = await file.read()
    else:
        try:
            form = await request.form()
            if "file" in form and hasattr(form["file"], "read"):
                chunk_bytes = await form["file"].read()
            if not upload_id and "upload_id" in form:
                upload_id = str(form["upload_id"])
            if chunk_index is None and "chunk_index" in form:
                chunk_index = str(form["chunk_index"])
            if total_chunks is None and "total_chunks" in form:
                total_chunks = str(form["total_chunks"])
            if not filename and "filename" in form:
                filename = str(form["filename"])
        except Exception:
            pass

        if not chunk_bytes:
            chunk_bytes = await request.body()

    if not upload_id:
        upload_id = f"up_{int(time.time())}"
    
    clean_upload_id = re.sub(r'[^a-zA-Z0-9_\-]', '', str(upload_id))[:64]
    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    temp_part_file = uploads_dir / f"chunk_{clean_upload_id}.part"

    try:
        c_idx = int(chunk_index) if chunk_index is not None else 0
        t_chunks = int(total_chunks) if total_chunks is not None else 1
    except Exception:
        c_idx, t_chunks = 0, 1

    # If first chunk, reset part file if it exists
    if c_idx == 0 and temp_part_file.exists():
        try:
            temp_part_file.unlink()
        except Exception:
            pass

    # Append chunk data to part file
    try:
        with open(temp_part_file, "ab") as f:
            if chunk_bytes:
                f.write(chunk_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed writing chunk {c_idx}: {str(e)}")

    is_last = (c_idx >= t_chunks - 1)

    if is_last:
        raw_name = filename or "uploaded_video.mp4"
        ext = Path(raw_name).suffix.lower()
        if ext not in [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".flv", ".3gp", ".wmv", ".mpeg", ".mpg"]:
            ext = ".mp4"
        clean_stem = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(raw_name).stem)[:45]
        timestamp = int(time.time())
        final_filename = f"video_{timestamp}_{clean_stem}{ext}"
        final_path = uploads_dir / final_filename

        if temp_part_file.exists():
            shutil.move(str(temp_part_file), str(final_path))
        
        rel_path = f"data/uploads/{final_filename}"
        return {
            "status": "COMPLETED",
            "chunk_index": c_idx,
            "total_chunks": t_chunks,
            "filename": final_filename,
            "file_path": str(final_path),
            "relative_path": rel_path,
            "url": f"/uploads/{final_filename}"
        }

    return {
        "status": "CHUNK_RECEIVED",
        "chunk_index": c_idx,
        "total_chunks": t_chunks
    }

