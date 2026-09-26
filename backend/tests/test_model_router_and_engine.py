import os
import json
import pytest
from pathlib import Path
from app.services.ai.router import ai_router, TaskUrgency, ModelTier
from app.services.ai.tensorrt_builder import tensorrt_builder

def test_ai_router_urgency_matrix():
    # 1. Critical Urgency -> Deep Tier
    crit_route = ai_router.route(task="person_detection", camera_id=1, scene="night", urgency="critical")
    assert crit_route["model_tier"] == ModelTier.DEEP.value
    assert crit_route["model_key"] == "yolo26l"
    assert crit_route["enable_deep_path"] == True
    assert crit_route["target_fps"] == 30

    # 2. High Urgency -> Primary Tier
    high_route = ai_router.route(task="vehicle_detection", camera_id=2, scene="day", urgency="high")
    assert high_route["model_tier"] == ModelTier.PRIMARY.value
    assert high_route["model_key"] == "yolo26m"
    assert high_route["enable_deep_path"] == True

    # 3. Background Urgency -> Fast Tier
    bg_route = ai_router.route(task="object_detection", camera_id=3, scene="day", urgency="background")
    assert bg_route["model_tier"] == ModelTier.FAST.value
    assert bg_route["model_key"] == "yolo26s"
    assert bg_route["enable_deep_path"] == False
    assert bg_route["target_fps"] == 5

def test_hardware_status_reporting():
    hw = ai_router.get_hardware_status()
    assert "gpu_available" in hw
    assert "gpu_count" in hw
    assert "process_ram_mb" in hw
    assert "cpu_utilization_pct" in hw
    assert hw["process_ram_mb"] > 0

def test_tensorrt_engine_builder_validation():
    # Non-existent engine validation
    val_fake = tensorrt_builder.validate_engine("non_existent_path.engine")
    assert val_fake["valid"] == False
    assert "not found" in val_fake["reason"].lower()

    # Hardware detection contract
    trt_avail, trt_msg = tensorrt_builder.is_tensorrt_available()
    assert isinstance(trt_avail, bool)
    assert isinstance(trt_msg, str)

def test_model_manifest_integrity():
    manifest_path = Path(__file__).parent.parent / "data" / "models" / "manifest.json"
    assert manifest_path.exists(), f"Manifest missing at {manifest_path}"

    with open(manifest_path, "r") as f:
        data = json.load(f)

    assert "manifest_version" in data
    assert "models" in data
    models = data["models"]
    
    # Verify core models registered in manifest
    assert "yolo26m_primary" in models
    assert "face_detector_yunet" in models
    assert "face_embedding_sface" in models

    assert models["yolo26m_primary"]["status"] == "DEPLOYED"
    assert models["face_detector_yunet"]["status"] == "DEPLOYED"
    assert models["face_embedding_sface"]["status"] == "DEPLOYED"
