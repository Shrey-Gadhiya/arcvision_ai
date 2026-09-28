import os
import re
import json
import time
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete, text
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.event_bus import event_bus
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
from app.services.snapshot_manager import snapshot_manager
from app.api.v1.auth import get_current_user

logger = logging.getLogger("arc_vision.cameras")

router = APIRouter(prefix="/cameras", tags=["Cameras"])

@router.get("/", response_model=List[CameraResponse])
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
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
async def get_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
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
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
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

class PurgeDataRequest(BaseModel):
    scope: str = "ALL_SURVEILLANCE_DATA"  # "ALL_SURVEILLANCE_DATA", "TRACKS_ONLY", "FACTORY_RESET"
    camera_id: Optional[int] = None
    purge_recordings: bool = True
    purge_snapshots: bool = True
    purge_events_and_detections: bool = True
    purge_incidents_and_evidence: bool = True
    delete_cameras: bool = False

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalars().first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    camera_name = cam.name

    # 1. Stop streamer and clear in-memory state
    try:
        stream_manager.stop_streamer(camera_id)
    except Exception as e:
        logger.warning(f"Error stopping streamer for camera #{camera_id}: {e}")

    try:
        snapshot_manager.clear_all_tracks(camera_id)
    except Exception as e:
        logger.warning(f"Error clearing snapshot tracks for camera #{camera_id}: {e}")

    # 2. Delete media directories on disk for this camera
    try:
        cam_rec_dir = Path(settings.RECORDINGS_DIR) / f"cam_{camera_id}"
        if cam_rec_dir.exists():
            shutil.rmtree(cam_rec_dir, ignore_errors=True)
            logger.info(f"Removed recordings directory on disk for Camera #{camera_id}")

        cam_snap_dir = Path(settings.SNAPSHOTS_DIR) / f"cam_{camera_id}"
        if cam_snap_dir.exists():
            shutil.rmtree(cam_snap_dir, ignore_errors=True)
            logger.info(f"Removed snapshots directory on disk for Camera #{camera_id}")
    except Exception as e:
        logger.warning(f"Error removing camera files from disk: {e}")

    # 3. Clean database records with raw foreign key protection
    try:
        await db.execute(text("PRAGMA foreign_keys = OFF"))

        child_tables = [
            ("track_observations", "camera_id"),
            ("case_findings", "camera_id"),
            ("notifications", "camera_id"),
            ("ptz_logs", "camera_id"),
            ("ptz_presets", "camera_id"),
            ("camera_ai_profiles", "camera_id"),
            ("anpr_records", "camera_id"),
            ("face_records", "camera_id"),
            ("evidences", "camera_id"),
            ("recording_segments", "camera_id"),
            ("tracked_snapshots", "camera_id"),
            ("rule_events", "camera_id"),
            ("detection_events", "camera_id"),
            ("tripwires", "camera_id"),
            ("zones", "camera_id"),
            ("incidents", "camera_id"),
        ]

        for table, col in child_tables:
            try:
                await db.execute(text(f"DELETE FROM {table} WHERE {col} = :cid"), {"cid": camera_id})
            except Exception as e:
                logger.debug(f"Note deleting from {table} for Camera #{camera_id}: {e}")

        # Topologies: clean from_camera_id and to_camera_id
        try:
            await db.execute(text("DELETE FROM camera_topologies WHERE from_camera_id = :cid OR to_camera_id = :cid"), {"cid": camera_id})
        except Exception:
            pass

        # Global tracks: decouple camera association
        try:
            await db.execute(text("UPDATE global_tracks SET current_camera_id = NULL WHERE current_camera_id = :cid"), {"cid": camera_id})
        except Exception:
            pass

        # Delete camera row
        await db.execute(text("DELETE FROM cameras WHERE id = :cid"), {"cid": camera_id})
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete Camera #{camera_id} from database: {e}")
        raise HTTPException(status_code=500, detail=f"Database error deleting camera: {str(e)}")
    finally:
        try:
            await db.execute(text("PRAGMA foreign_keys = ON"))
        except Exception:
            pass

    # 4. Audit Log
    try:
        audit = AuditLog(
            username="operator",
            user_role="OPERATOR",
            action="DELETE_CAMERA",
            resource_type="CAMERA",
            resource_id=str(camera_id),
            details_json=json.dumps({"camera_id": camera_id, "camera_name": camera_name, "status": "DELETED"})
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass

    # 5. Broadcast real-time deletion over WebSocket
    try:
        await event_bus.publish("camera:deleted", {
            "camera_id": camera_id,
            "camera_name": camera_name
        })
    except Exception:
        pass

    return None

@router.post("/purge-all-data")
async def purge_all_data(
    req: PurgeDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Comprehensive Tactical Purge:
    - Removes all media files (recordings, snapshots, evidence) from disk.
    - Clears all AI detections, rules events, tracked snapshots, incidents, and recordings from DB.
    - Flushes in-memory tracking states and Kalman filters.
    - Reclaims disk space and compacts SQLite database with VACUUM.
    """
    total_files_deleted = 0
    total_freed_bytes = 0

    # 1. In-memory flush
    streamers_reset = stream_manager.clear_all_tracked_objects(req.camera_id)
    snapshot_manager.clear_all_tracks(req.camera_id)

    # 2. Disk media cleanup
    if req.camera_id is not None:
        # Specific camera media purge
        target_dirs = []
        if req.purge_recordings:
            target_dirs.append(Path(settings.RECORDINGS_DIR) / f"cam_{req.camera_id}")
        if req.purge_snapshots:
            target_dirs.append(Path(settings.SNAPSHOTS_DIR) / f"cam_{req.camera_id}")

        for p in target_dirs:
            if p.exists():
                for root, _, files in os.walk(p):
                    for f in files:
                        fp = Path(root) / f
                        try:
                            total_freed_bytes += fp.stat().st_size
                            fp.unlink()
                            total_files_deleted += 1
                        except Exception:
                            pass
                shutil.rmtree(p, ignore_errors=True)
    else:
        # Global purge
        disk_dirs = []
        if req.purge_recordings:
            disk_dirs.append(settings.RECORDINGS_DIR)
        if req.purge_snapshots:
            disk_dirs.append(settings.SNAPSHOTS_DIR)
        if req.purge_incidents_and_evidence:
            disk_dirs.append(settings.EVIDENCE_DIR)

        for d in disk_dirs:
            if d.exists():
                for root, _, files in os.walk(d):
                    for f in files:
                        fp = Path(root) / f
                        try:
                            total_freed_bytes += fp.stat().st_size
                            fp.unlink()
                            total_files_deleted += 1
                        except Exception:
                            pass
                for root, dirs, _ in os.walk(d, topdown=False):
                    for sub in dirs:
                        try:
                            (Path(root) / sub).rmdir()
                        except Exception:
                            pass
            d.mkdir(parents=True, exist_ok=True)

    # 3. Database Purge
    records_purged = 0
    try:
        await db.execute(text("PRAGMA foreign_keys = OFF"))

        tables_to_clear = []
        if req.purge_events_and_detections:
            tables_to_clear.extend(["detection_events", "rule_events"])
        if req.purge_snapshots:
            tables_to_clear.append("tracked_snapshots")
        if req.purge_recordings:
            tables_to_clear.append("recording_segments")
        if req.purge_incidents_and_evidence:
            tables_to_clear.extend(["face_records", "anpr_records", "evidences", "incidents", "case_findings", "notifications"])
        
        tables_to_clear.extend(["track_observations", "global_tracks", "ptz_logs"])

        if req.camera_id is not None:
            for t in tables_to_clear:
                try:
                    res = await db.execute(text(f"DELETE FROM {t} WHERE camera_id = :cid"), {"cid": req.camera_id})
                    records_purged += res.rowcount if hasattr(res, "rowcount") and res.rowcount > 0 else 0
                except Exception:
                    pass
        else:
            for t in tables_to_clear:
                try:
                    res = await db.execute(text(f"DELETE FROM {t}"))
                    records_purged += res.rowcount if hasattr(res, "rowcount") and res.rowcount > 0 else 0
                except Exception:
                    pass

        # If factory reset or delete_cameras requested
        if req.delete_cameras or req.scope == "FACTORY_RESET":
            # Stop all streamers
            for c_id in list(stream_manager.get_all_streamers().keys()):
                stream_manager.stop_streamer(c_id)
            for t in ["tripwires", "zones", "camera_ai_profiles", "camera_topologies", "ptz_presets", "cameras"]:
                try:
                    await db.execute(text(f"DELETE FROM {t}"))
                except Exception:
                    pass

        await db.commit()

        # Compact SQLite database
        try:
            await db.execute(text("VACUUM"))
        except Exception:
            pass

    except Exception as e:
        await db.rollback()
        logger.error(f"Error purging database records: {e}")
    finally:
        try:
            await db.execute(text("PRAGMA foreign_keys = ON"))
        except Exception:
            pass

    # Broadcast event
    try:
        await event_bus.publish("data:purged", {
            "scope": req.scope,
            "camera_id": req.camera_id,
            "freed_mb": round(total_freed_bytes / (1024 * 1024), 2),
            "files_deleted": total_files_deleted,
            "records_purged": records_purged
        })
    except Exception:
        pass

    return {
        "status": "SUCCESS",
        "scope": req.scope,
        "files_deleted": total_files_deleted,
        "records_purged": records_purged,
        "freed_mb": round(total_freed_bytes / (1024 * 1024), 2),
        "freed_gb": round(total_freed_bytes / (1024 ** 3), 2),
        "streamers_reset": streamers_reset,
        "message": f"Successfully purged surveillance data ({total_files_deleted} files removed, {round(total_freed_bytes / (1024*1024), 2)} MB freed)."
    }


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
    file: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    upload: Optional[UploadFile] = File(None)
):
    """
    Uploads an MP4 / video file to serve as a custom CCTV camera feed source.
    High-reliability single-stream upload with 4MB buffer and Windows-safe file operations.
    """
    import asyncio
    actual_file = file or video or upload
    raw_name = "uploaded_video.mp4"

    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())

    if actual_file is not None and hasattr(actual_file, "filename") and actual_file.filename:
        raw_name = actual_file.filename
    else:
        try:
            form = await request.form()
            for key in ["file", "video", "upload", "media"]:
                if key in form and hasattr(form[key], "filename") and form[key].filename:
                    actual_file = form[key]
                    raw_name = actual_file.filename
                    break
        except Exception:
            pass

    ext = Path(raw_name).suffix.lower()
    allowed_exts = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".flv", ".3gp", ".wmv", ".mpeg", ".mpg"]
    if ext not in allowed_exts:
        ext = ".mp4"

    clean_basename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(raw_name).stem)[:45]
    safe_name = f"video_{timestamp}_{clean_basename}{ext}"
    target_path = uploads_dir / safe_name
    temp_target = uploads_dir / f"tmp_{timestamp}_{clean_basename}.part"

    try:
        if actual_file is not None:
            with open(temp_target, "wb") as buffer:
                if hasattr(actual_file, "file") and actual_file.file:
                    shutil.copyfileobj(actual_file.file, buffer, length=4 * 1024 * 1024)
                elif hasattr(actual_file, "read"):
                    while chunk := await actual_file.read(4 * 1024 * 1024):
                        buffer.write(chunk)
        else:
            # Direct binary body stream
            body = await request.body()
            if not body or len(body) < 100:
                raise HTTPException(status_code=400, detail="No video file provided.")
            with open(temp_target, "wb") as f:
                f.write(body)

        # Windows-safe atomic move with retries to prevent antivirus / indexing lockups
        moved = False
        for attempt in range(12):
            try:
                if target_path.exists():
                    target_path.unlink()
                shutil.move(str(temp_target), str(target_path))
                moved = True
                break
            except (PermissionError, OSError):
                if attempt < 11:
                    await asyncio.sleep(0.08)
                else:
                    try:
                        shutil.copy2(str(temp_target), str(target_path))
                        temp_target.unlink()
                        moved = True
                    except Exception:
                        pass

        if not moved and not target_path.exists():
            raise HTTPException(status_code=500, detail="Failed to finalize video file on disk.")

    except HTTPException:
        raise
    except Exception as e:
        if temp_target.exists():
            try:
                temp_target.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to write video file: {str(e)}")
    finally:
        if actual_file is not None and hasattr(actual_file, "close"):
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
    file: Optional[UploadFile] = File(None)
):
    """
    High-reliability chunked upload endpoint.
    Accepts binary chunks and appends with Windows-safe file locking handlers.
    """
    import asyncio
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

    # If first chunk, reset part file if it exists with retry
    if c_idx == 0 and temp_part_file.exists():
        for _ in range(5):
            try:
                temp_part_file.unlink()
                break
            except Exception:
                await asyncio.sleep(0.05)

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
            for attempt in range(12):
                try:
                    if final_path.exists():
                        final_path.unlink()
                    shutil.move(str(temp_part_file), str(final_path))
                    break
                except (PermissionError, OSError):
                    if attempt < 11:
                        await asyncio.sleep(0.08)
                    else:
                        try:
                            shutil.copy2(str(temp_part_file), str(final_path))
                            temp_part_file.unlink()
                        except Exception:
                            pass

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

