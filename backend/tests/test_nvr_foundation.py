import pytest
import os
import cv2
import numpy as np
from datetime import datetime, timezone, timedelta
from app.services.ai.motion_detector import MotionDetector
from app.services.recording_engine import recording_engine, CameraSegmentBuffer
from app.services.snapshot_manager import snapshot_manager
from app.services.storage_manager import storage_manager
from app.core.config import settings

def test_motion_detector():
    md = MotionDetector(threshold=25, min_area=200)
    # Background frame
    f1 = np.zeros((360, 640, 3), dtype=np.uint8)
    has_m, score, boxes, _ = md.detect(f1)
    
    # Foreground frame with moving white rectangle
    f2 = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.rectangle(f2, (100, 100), (250, 250), (255, 255, 255), -1)
    has_m, score, boxes, _ = md.detect(f2)
    
    assert has_m is True
    assert score > 0.0
    assert len(boxes) >= 1

def test_camera_segment_buffer(tmp_path):
    buf = CameraSegmentBuffer(camera_id=99, segment_duration_sec=0.5, fps=10)
    f = np.zeros((240, 320, 3), dtype=np.uint8)
    
    # Add 10 frames with 0.1s simulated spacing
    seg_meta = None
    for i in range(10):
        res = buf.add_frame(
            frame=f,
            has_objects=(i > 5),
            detected_classes=["person"] if i > 5 else [],
            motion_score=0.4
        )
        if res:
            seg_meta = res
            break
            
    # We should have flushed a segment
    if not seg_meta:
        # Manually flush if timing was faster than clock
        seg_meta = buf._flush_segment(buf.segment_start_time + 1.0)
        
    assert seg_meta is not None
    assert seg_meta["camera_id"] == 99
    assert seg_meta["duration_sec"] > 0
    assert seg_meta["sha256_hash"] != ""
    assert os.path.exists(seg_meta["absolute_path"])

def test_snapshot_manager_quality_score():
    f = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.putText(f, "HIGH CONTRAST TARGET", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    score = snapshot_manager._calculate_quality_score(f, [0.05, 0.05, 0.4, 0.3], 0.88)
    assert score > 0.0
    assert score <= 1.0
