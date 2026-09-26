import pytest
import numpy as np
from app.services.ai.base import BaseDetectorAdapter, Detection, DetectorStatus
from app.services.ai.yolo_adapter import YOLODetectorAdapter
from app.services.ai.onnx_adapter import ONNXDetectorAdapter
from app.services.ai.detector_registry import detector_registry

def test_detection_dataclass():
    det = Detection(
        class_name="person",
        confidence=0.895,
        box=[0.1, 0.2, 0.5, 0.8],
        track_id=12,
        attributes={"speed": 1.4}
    )
    d_dict = det.to_dict()
    assert d_dict["class_name"] == "person"
    assert d_dict["confidence"] == 0.895
    assert d_dict["track_id"] == 12
    assert d_dict["box"] == [0.1, 0.2, 0.5, 0.8]

def test_yolo_adapter_contract():
    adapter = YOLODetectorAdapter(model_path="yolov8n.pt")
    assert isinstance(adapter, BaseDetectorAdapter)
    assert adapter.name == "YOLOv8n Detector"
    assert adapter.status in [DetectorStatus.LOADED, DetectorStatus.ERROR]
    
    classes = adapter.get_supported_classes()
    assert "person" in classes
    assert "car" in classes
    assert "truck" in classes

    telemetry = adapter.get_telemetry()
    assert "inference_latency_ms" in telemetry
    assert "inference_fps" in telemetry
    assert "status" in telemetry

def test_onnx_adapter_graceful_handling():
    # Test with non-existent ONNX model
    adapter = ONNXDetectorAdapter(model_path="non_existent_weights.onnx")
    assert isinstance(adapter, BaseDetectorAdapter)
    assert adapter.status in [DetectorStatus.ERROR, DetectorStatus.NOT_SUPPORTED]
    
    # Inference on empty or uninitialized returns empty list safely
    dets = adapter.detect(np.zeros((100, 100, 3), dtype=np.uint8))
    assert dets == []

def test_detector_registry():
    default_det = detector_registry.get_detector()
    assert default_det is not None
    assert isinstance(default_det, BaseDetectorAdapter)

    all_dets = detector_registry.list_detectors()
    assert len(all_dets) >= 2
    keys = [d["key"] for d in all_dets]
    assert "yolov8n" in keys
    assert "onnx_yolo" in keys

def test_yolo26_adapter_loading_and_inference():
    """Verify that real YOLO26 models load, fingerprint as YOLO26, and execute inference."""
    from pathlib import Path
    yolo26_path = Path("data/models/detection/yolo26/yolo26m.pt")
    if yolo26_path.exists():
        adapter = YOLODetectorAdapter(
            name="YOLO26m Primary Perimeter Detector",
            model_path=str(yolo26_path),
            model_version="26.0.0",
            device="cpu"
        )
        assert adapter.status == DetectorStatus.LOADED
        assert adapter.fingerprint.actual_family == "YOLO26"
        assert adapter.fingerprint.actual_variant == "YOLO26m"
        assert adapter.fingerprint.parameter_count > 20_000_000
        
        # Run test inference on synthetic frame
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = adapter.detect(img)
        assert isinstance(detections, list)

