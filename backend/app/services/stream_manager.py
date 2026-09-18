import asyncio
import logging
from typing import Dict, Optional, List, Any
import psutil

from app.services.camera_streamer import CameraStreamer
from app.services.demo_generator import ensure_demo_assets
from app.services.recording_engine import recording_engine
from app.core.config import settings
from app.core.event_bus import event_bus

logger = logging.getLogger("arc_vision.stream_manager")

class StreamManager:
    def __init__(self):
        self._streamers: Dict[int, CameraStreamer] = {}
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        self._main_loop = loop
        for streamer in self._streamers.values():
            streamer.set_main_loop(loop)

    def start_streamer(
        self,
        camera_id: int,
        camera_name: str,
        stream_url: str,
        stream_type: str = "SYNTHETIC",
        target_fps: int = 15,
        zones: List[Dict[str, Any]] = None,
        tripwires: List[Dict[str, Any]] = None,
        is_night_mode: bool = True,
        anpr_enabled: bool = True,
        main_loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> CameraStreamer:
        if camera_id in self._streamers:
            self._streamers[camera_id].stop()

        target_loop = main_loop or self._main_loop
        if target_loop is None:
            try:
                target_loop = asyncio.get_running_loop()
                self._main_loop = target_loop
            except RuntimeError:
                pass

        streamer = CameraStreamer(
            camera_id=camera_id,
            camera_name=camera_name,
            stream_url=stream_url,
            stream_type=stream_type,
            target_fps=target_fps,
            zones=zones,
            tripwires=tripwires,
            is_night_mode=is_night_mode,
            anpr_enabled=anpr_enabled,
            main_loop=target_loop
        )
        streamer.start()
        self._streamers[camera_id] = streamer
        logger.info(f"StreamManager registered Camera #{camera_id}: {camera_name}")
        return streamer

    def stop_streamer(self, camera_id: int):
        if camera_id in self._streamers:
            self._streamers[camera_id].stop()
            del self._streamers[camera_id]
        recording_engine.remove_camera(camera_id)

    def get_streamer(self, camera_id: int) -> Optional[CameraStreamer]:
        return self._streamers.get(camera_id)

    def get_all_streamers(self) -> Dict[int, CameraStreamer]:
        return dict(self._streamers)

    def get_system_health(self) -> Dict[str, Any]:
        """Collects CPU, RAM, Disk, and Camera Stream health metrics."""
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(settings.BASE_DIR))

        cam_stats = []
        for cam_id, streamer in self._streamers.items():
            cam_stats.append({
                "camera_id": cam_id,
                "name": streamer.camera_name,
                "status": streamer.status,
                "fps": streamer.current_fps,
                "target_fps": streamer.target_fps,
                "latency_ms": streamer.latency_ms,
                "dropped_frames": streamer.drop_count,
                "resolution": f"{getattr(streamer, 'resolution_w', 1280)}x{getattr(streamer, 'resolution_h', 720)}",
                "frames_processed": streamer.frame_count,
                "last_frame_time": streamer.last_frame_time,
                "is_running": streamer.is_running
            })

        return {
            "cpu_usage_pct": cpu_pct,
            "memory_usage_pct": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "active_cameras": len(self._streamers),
            "cameras": cam_stats
        }

stream_manager = StreamManager()
