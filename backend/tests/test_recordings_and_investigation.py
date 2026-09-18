import os
import json
import zipfile
import hashlib
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import HTTPException

from app.models.recording import RecordingSegment, SegmentType
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.camera import Camera, CameraRecordingMode
from app.models.evidence import Evidence, EvidenceType
from app.services.recording_engine import CameraSegmentBuffer, RecordingEngine, compute_sha256
from app.services.evidence_manager import EvidenceManager
from app.services.storage_manager import StorageManager
from app.api.v1.recordings import _validate_safe_path
from app.core.config import settings

def test_camera_segment_buffer_creation_and_metadata(tmp_path):
    """Verifies that CameraSegmentBuffer generates segments with valid codec, resolution, and hashes."""
    import time
    buf = CameraSegmentBuffer(camera_id=1, segment_duration_sec=0.05, fps=15)
    buf.recordings_dir = tmp_path

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Add initial frames
    for _ in range(5):
        buf.add_frame(
            frame=frame,
            has_objects=True,
            detected_classes=["person", "car"],
            motion_score=0.45,
            is_incident_event=True
        )
    
    # Wait for duration threshold to elapse
    time.sleep(0.08)

    # Add next frame to trigger flush
    seg_meta = buf.add_frame(
        frame=frame,
        has_objects=True,
        detected_classes=["person"],
        motion_score=0.5,
        is_incident_event=True
    )

    assert seg_meta is not None
    assert seg_meta["camera_id"] == 1
    assert seg_meta["segment_type"] == SegmentType.EVENT
    assert seg_meta["codec"] == "H.264 / MP4"
    assert seg_meta["resolution"] == "1280x720"
    assert seg_meta["has_objects"] is True
    assert "person" in seg_meta["objects_detected_json"]
    assert seg_meta["sha256_hash"] != ""
    assert os.path.exists(seg_meta["absolute_path"])

def test_path_traversal_prevention():
    """Verifies that malicious path traversal attempts are detected and blocked."""
    base_dir = settings.RECORDINGS_DIR

    # Valid safe relative paths
    safe_p = _validate_safe_path("cam_1/20260918/seg_1_2.mp4", base_dir)
    assert str(safe_p).startswith(str(base_dir.resolve()))

    # Path traversal attack
    with pytest.raises(HTTPException) as exc_info:
        _validate_safe_path("../../../../../etc/passwd", base_dir)
    assert exc_info.value.status_code == 400
    assert "Path traversal" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info:
        _validate_safe_path("..\\..\\..\\windows\\system32\\cmd.exe", base_dir)
    assert exc_info.value.status_code == 400

@pytest.mark.anyio
async def test_event_recording_correlation():
    """Verifies that event windows are correctly correlated into pre-event, event, and post-event intervals."""
    engine = RecordingEngine()
    
    # Mock database session with in-memory segments
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(seconds=60)
    t1 = now - timedelta(seconds=30)
    t2 = now
    t3 = now + timedelta(seconds=30)
    t4 = now + timedelta(seconds=60)

    # Correlate an event occurring from t1 to t2
    # Pre-event: t0 to t1, Event: t1 to t2, Post-event: t2 to t3
    class MockResult:
        def __init__(self, items):
            self.items = items
        def scalars(self):
            return self
        def all(self):
            return self.items

    class MockSession:
        async def execute(self, stmt):
            s_pre = RecordingSegment(
                id=1, camera_id=1, start_time=t0, end_time=t1, duration_sec=30.0,
                file_path="/recordings/seg1.mp4", file_size_bytes=1000,
                segment_type=SegmentType.CONTINUOUS, motion_score=0.1,
                has_objects=False, objects_detected_json="[]", sha256_hash="hash1",
                is_protected=False, codec="H.264", resolution="1280x720"
            )
            s_evt = RecordingSegment(
                id=2, camera_id=1, start_time=t1, end_time=t2, duration_sec=30.0,
                file_path="/recordings/seg2.mp4", file_size_bytes=2000,
                segment_type=SegmentType.EVENT, motion_score=0.8,
                has_objects=True, objects_detected_json='["person"]', sha256_hash="hash2",
                is_protected=True, codec="H.264", resolution="1280x720"
            )
            s_post = RecordingSegment(
                id=3, camera_id=1, start_time=t2, end_time=t3, duration_sec=30.0,
                file_path="/recordings/seg3.mp4", file_size_bytes=1000,
                segment_type=SegmentType.CONTINUOUS, motion_score=0.1,
                has_objects=False, objects_detected_json="[]", sha256_hash="hash3",
                is_protected=False, codec="H.264", resolution="1280x720"
            )
            return MockResult([s_pre, s_evt, s_post])

    res = await engine.correlate_event_window(
        camera_id=1,
        event_start=t1,
        event_end=t2,
        pre_sec=15,
        post_sec=15,
        session=MockSession()
    )

    assert res["total_segments"] == 3
    assert res["pre_event_segment"] is not None
    assert res["pre_event_segment"]["id"] == 1
    assert len(res["event_segments"]) == 1
    assert res["event_segments"][0]["id"] == 2
    assert res["post_event_segment"] is not None
    assert res["post_event_segment"]["id"] == 3

def test_evidence_package_export_and_verification(tmp_path):
    """Verifies that evidence ZIP packages are generated with valid manifest and tamper verification."""
    mgr = EvidenceManager()
    mgr.evidence_dir = tmp_path

    # Create dummy evidence files
    snap_p = tmp_path / "snap_test.jpg"
    snap_p.write_bytes(b"TEST_IMAGE_BYTES_12345")
    snap_hash = compute_sha256(snap_p)

    clip_p = tmp_path / "clip_test.mp4"
    clip_p.write_bytes(b"TEST_VIDEO_BYTES_67890")
    clip_hash = compute_sha256(clip_p)

    pkg_dir = tmp_path / "packages"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pkg_file = pkg_dir / "evidence_package_INC-TEST-01.zip"

    manifest_files = [
        {"path": "snapshots/snap_test.jpg", "file_type": "SNAPSHOT", "file_size_bytes": len(b"TEST_IMAGE_BYTES_12345"), "sha256_hash": snap_hash},
        {"path": "video/clip_test.mp4", "file_type": "CLIP", "file_size_bytes": len(b"TEST_VIDEO_BYTES_67890"), "sha256_hash": clip_hash}
    ]
    all_h = "".join(f["sha256_hash"] for f in sorted(manifest_files, key=lambda x: x["path"]))
    sig = hashlib.sha256(all_h.encode("utf-8")).hexdigest()

    manifest_data = {
        "incident_id": 1,
        "incident_code": "INC-TEST-01",
        "camera_id": 1,
        "camera_name": "Test Cam",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "test_investigator",
        "summary": "Border Intrusion Test",
        "threat_score": 90.0,
        "total_files": 2,
        "files": manifest_files,
        "manifest_signature": sig
    }

    with zipfile.ZipFile(str(pkg_file), "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest_data).encode("utf-8"))
        zf.write(str(snap_p), arcname="snapshots/snap_test.jpg")
        zf.write(str(clip_p), arcname="video/clip_test.mp4")

    # 1. Verify intact package
    ver_res = mgr.verify_evidence_package("evidence_package_INC-TEST-01.zip")
    assert ver_res["is_valid"] is True
    assert ver_res["status"] == "VERIFIED_TAMPER_FREE"
    assert ver_res["verified_files_count"] == 2
    assert len(ver_res["tampered_files"]) == 0

    # 2. Tamper with package (overwrite image bytes)
    tampered_pkg_file = pkg_dir / "evidence_package_TAMPERED.zip"
    with zipfile.ZipFile(str(tampered_pkg_file), "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest_data).encode("utf-8"))
        zf.writestr("snapshots/snap_test.jpg", b"TAMPERED_MODIFIED_IMAGE")
        zf.write(str(clip_p), arcname="video/clip_test.mp4")

    tamper_res = mgr.verify_evidence_package("evidence_package_TAMPERED.zip")
    assert tamper_res["is_valid"] is False
    assert tamper_res["status"] == "TAMPER_DETECTED"
    assert len(tamper_res["tampered_files"]) > 0
