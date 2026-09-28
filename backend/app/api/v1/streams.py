import asyncio
import time
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from app.services.stream_manager import stream_manager

router = APIRouter(prefix="/streams", tags=["Live Streams"])

async def frame_generator(camera_id: int, annotated: bool = True, fps: int = 15):
    """
    Generates standard multipart/x-mixed-replace MJPEG stream frames with zero-lag backpressure management.
    Auto-starts camera streamer if not running and streams latest available frames.
    """
    streamer = stream_manager.get_streamer(camera_id)
    if not streamer:
        from app.core.database import AsyncSessionLocal
        from app.models.camera import Camera
        from sqlalchemy import select
        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Camera).where(Camera.id == camera_id))
                cam = res.scalars().first()
                if cam:
                    streamer = stream_manager.start_streamer(
                        camera_id=cam.id,
                        camera_name=cam.name,
                        stream_url=cam.rtsp_url,
                        stream_type=cam.stream_type.value,
                        target_fps=cam.target_fps,
                        is_night_mode=bool(cam.night_mode_enabled),
                        anpr_enabled=bool(cam.anpr_enabled)
                    )
        except Exception:
            pass

    last_count = -1
    effective_fps = max(5, min(fps, 30))
    target_interval = 1.0 / effective_fps
    last_sent_time = 0.0

    try:
        while streamer and streamer.is_running:
            now = time.time()
            # Enforce frame pacing and anti-lag skipping:
            # If client or network lags, intermediate frames are skipped, always yielding the LATEST frame!
            if (now - last_sent_time) >= target_interval:
                curr_count = streamer.frame_count
                if curr_count != last_count or curr_count == 0:
                    last_count = curr_count
                    last_sent_time = now
                    jpeg_bytes = streamer.get_jpeg_bytes(annotated=annotated)
                    if jpeg_bytes is not None:
                        yield (
                            b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n'
                        )
            await asyncio.sleep(0.01)
    except (asyncio.CancelledError, GeneratorExit):
        pass
    except Exception:
        pass

@router.get("/{camera_id}/live.mjpg")
async def get_live_mjpeg(camera_id: int, annotated: bool = True, fps: int = 15):
    return StreamingResponse(
        frame_generator(camera_id, annotated=annotated, fps=fps),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
            "Connection": "close"
        }
    )

@router.get("/{camera_id}/snapshot.jpg")
async def get_snapshot(camera_id: int, annotated: bool = True):
    streamer = stream_manager.get_streamer(camera_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Camera stream worker not running")

    jpeg_bytes = streamer.get_jpeg_bytes(annotated=annotated)
    if jpeg_bytes is None:
        raise HTTPException(status_code=503, detail="No frame available yet")

    return Response(content=jpeg_bytes, media_type="image/jpeg")

@router.get("/{camera_id}/detections")
async def get_active_detections(camera_id: int):
    streamer = stream_manager.get_streamer(camera_id)
    if not streamer:
        return {"camera_id": camera_id, "detections": []}

    return {
        "camera_id": camera_id,
        "fps": streamer.current_fps,
        "detections": [d.to_dict() for d in streamer.latest_detections]
    }

@router.post("/clear-tracks")
async def clear_tracks(camera_id: int = None):
    """Flushes active multi-object tracker states on camera streams."""
    cleared = stream_manager.clear_all_tracked_objects(camera_id)
    return {"status": "SUCCESS", "streamers_cleared": cleared}

