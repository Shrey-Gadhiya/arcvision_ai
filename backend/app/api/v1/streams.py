import asyncio
import time
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from app.services.stream_manager import stream_manager

router = APIRouter(prefix="/streams", tags=["Live Streams"])

async def frame_generator(camera_id: int, annotated: bool = True):
    """
    Generates standard multipart/x-mixed-replace MJPEG stream frames.
    Event-driven by streamer frame count to eliminate buffer lags and tunnel queue congestion.
    """
    streamer = stream_manager.get_streamer(camera_id)
    if not streamer:
        return

    last_count = -1
    fps = max(20, streamer.target_fps)
    max_sleep = 1.0 / fps

    try:
        while streamer.is_running:
            curr_count = streamer.frame_count
            if curr_count != last_count:
                last_count = curr_count
                jpeg_bytes = streamer.get_jpeg_bytes(annotated=annotated)
                if jpeg_bytes is not None:
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n'
                    )
            await asyncio.sleep(0.015)
    except (asyncio.CancelledError, GeneratorExit):
        pass
    except Exception:
        pass

@router.get("/{camera_id}/live.mjpg")
async def get_live_mjpeg(camera_id: int, annotated: bool = True):
    streamer = stream_manager.get_streamer(camera_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Camera stream worker not running")

    return StreamingResponse(
        frame_generator(camera_id, annotated=annotated),
        media_type="multipart/x-mixed-replace; boundary=frame"
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
