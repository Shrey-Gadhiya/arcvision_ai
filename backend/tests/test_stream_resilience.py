import pytest
from app.services.stream_manager import stream_manager
from app.services.camera_streamer import CameraStreamer

def test_stream_manager_system_health():
    health = stream_manager.get_system_health()
    assert "cpu_usage_pct" in health
    assert "memory_usage_pct" in health
    assert "memory_used_gb" in health
    assert "disk_free_gb" in health
    assert "active_cameras" in health
    assert "cameras" in health
    assert isinstance(health["cameras"], list)

def test_camera_streamer_initialization():
    streamer = CameraStreamer(
        camera_id=999,
        camera_name="Test Streamer Resilience",
        stream_url="data/demos/sample.mp4",
        stream_type="FILE",
        target_fps=25
    )
    assert streamer.camera_id == 999
    assert streamer.status == "CONNECTING"
    assert streamer.drop_count == 0
    assert streamer.frame_count == 0
    assert hasattr(streamer, "motion_masks")
