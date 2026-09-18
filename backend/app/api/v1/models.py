import json
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.camera import Camera
from app.models.model_registry import AIModel, AIModelStatus, AIModelTask
from app.models.camera_profile import CameraAIProfile
from app.schemas.all_schemas import (
    AIModelCreate,
    AIModelUpdate,
    AIModelResponse,
    CameraAIProfileCreate,
    CameraAIProfileUpdate,
    CameraAIProfileResponse,
    PerceptionTelemetryResponse
)
from app.services.ai.detector import detector_service
from app.services.ai.face.service import face_service
from app.services.ai.perception.orchestrator import perception_orchestrator
from app.services.ai.perception.base import PerceptionTask, ModelStatus

router = APIRouter(prefix="/models", tags=["AI Model Registry & Perception Center"])

@router.get("/", response_model=List[AIModelResponse])
async def list_ai_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIModel).order_by(AIModel.id))
    models = list(result.scalars().all())
    existing_names = {m.name for m in models}

    # 1. YOLO Perimeter Detector
    if "YOLOv8n Perimeter Detector" not in existing_names:
        yolo_model = AIModel(
            name="YOLOv8n Perimeter Detector",
            version="8.1.0",
            task=AIModelTask.DETECTION,
            provider="Ultralytics YOLO",
            model_path="yolov8n.pt",
            format="PyTorch (.pt)",
            input_resolution="640x640",
            classes_json=json.dumps(["person", "car", "truck", "bus", "motorcycle", "bicycle", "backpack", "dog"]),
            device="CUDA:0" if getattr(detector_service, 'device', 'cpu') != 'cpu' else "CPU",
            status=AIModelStatus.LOADED,
            inference_latency_ms=18.5,
            inference_fps=35.0,
            memory_mb=185.0
        )
        db.add(yolo_model)
        models.append(yolo_model)

    # 2. YuNet Face Detector
    if "YuNet Neural Face Detector" not in existing_names:
        det_status = AIModelStatus.LOADED if face_service.detector_adapter.status.value == "LOADED" else AIModelStatus.STANDBY
        yunet_model = AIModel(
            name="YuNet Neural Face Detector",
            version="2023mar",
            task=AIModelTask.FACE_DETECTION,
            provider="OpenCV ONNX",
            model_path="data/models/face_detection_yunet_2023mar.onnx",
            format="ONNX (.onnx)",
            input_resolution="320x320",
            classes_json=json.dumps(["face", "landmarks_5pt"]),
            device=face_service.detector_adapter.device.upper(),
            status=det_status,
            inference_latency_ms=face_service.detector_adapter.latency_ms or 12.0,
            inference_fps=face_service.detector_adapter.fps or 60.0,
            memory_mb=45.0
        )
        db.add(yunet_model)
        models.append(yunet_model)

    # 3. SFace Face Recognizer
    if "SFace Biometric Face Recognizer" not in existing_names:
        rec_status = AIModelStatus.LOADED if face_service.embedding_adapter.status.value == "LOADED" else AIModelStatus.STANDBY
        sface_model = AIModel(
            name="SFace Biometric Face Recognizer",
            version="2021dec",
            task=AIModelTask.FACE_RECOGNITION,
            provider="OpenCV ONNX",
            model_path="data/models/face_recognition_sface_2021dec.onnx",
            format="ONNX (.onnx)",
            input_resolution="112x112",
            classes_json=json.dumps(["128d_embedding_vector"]),
            device=face_service.embedding_adapter.device.upper(),
            status=rec_status,
            inference_latency_ms=face_service.embedding_adapter.latency_ms or 15.0,
            inference_fps=50.0,
            memory_mb=65.0
        )
        db.add(sface_model)
        models.append(sface_model)

    # 4. Pose Estimator
    if "YOLOv8n-Pose Neural Keypoint Estimator" not in existing_names:
        pose_adapter = perception_orchestrator.pose_adapter
        pose_status = AIModelStatus.LOADED if pose_adapter.is_loaded else AIModelStatus.STANDBY
        pose_model = AIModel(
            name="YOLOv8n-Pose Neural Keypoint Estimator",
            version="8.1.0",
            task=AIModelTask.POSE_ESTIMATION,
            provider="Ultralytics / ONNX Runtime",
            model_path="data/models/yolov8n-pose.onnx",
            format="ONNX (.onnx)",
            input_resolution="640x640",
            classes_json=json.dumps(["person_keypoints_17pt"]),
            device=pose_adapter.device,
            status=pose_status,
            inference_latency_ms=pose_adapter.latency_ms or 14.5,
            inference_fps=pose_adapter.fps or 45.0,
            memory_mb=pose_adapter.memory_mb or 75.0
        )
        db.add(pose_model)
        models.append(pose_model)

    # 5. Fall Detector
    if "Kinematic & Geometric Fall Detection Engine" not in existing_names:
        fall_adapter = perception_orchestrator.fall_detector
        fall_model = AIModel(
            name="Kinematic & Geometric Fall Detection Engine",
            version="2.0.0",
            task=AIModelTask.FALL_DETECTION,
            provider="ARC-VISION Biomechanical Intelligence",
            model_path="app/services/ai/perception/fall_detector.py",
            format="Kinematic & Geometric Analyzer",
            input_resolution="Kinematic Trajectory & Bounding Geometry",
            classes_json=json.dumps(["fall_incident", "person_down", "slip_trip_fall"]),
            device="CPU",
            status=AIModelStatus.LOADED,
            inference_latency_ms=fall_adapter.latency_ms or 0.8,
            inference_fps=150.0,
            memory_mb=fall_adapter.memory_mb or 8.0
        )
        db.add(fall_model)
        models.append(fall_model)

    # 6. Pyros Fire & Smoke Detector
    if "Pyros-AI Fire & Smoke Neural Detector" not in existing_names:
        fire_adapter = perception_orchestrator.fire_smoke_adapter
        fire_status = AIModelStatus.LOADED if fire_adapter.is_loaded else AIModelStatus.STANDBY
        fire_model = AIModel(
            name="Pyros-AI Fire & Smoke Neural Detector",
            version="2.1.0",
            task=AIModelTask.FIRE_SMOKE_DETECTION,
            provider="Custom Trained YOLO / ONNX",
            model_path="data/models/fire_smoke_yolov8s.onnx",
            format="ONNX (.onnx)",
            input_resolution="640x640",
            classes_json=json.dumps(["fire", "smoke"]),
            device=fire_adapter.device,
            status=fire_status,
            inference_latency_ms=fire_adapter.latency_ms or 0.0,
            inference_fps=fire_adapter.fps or 0.0,
            memory_mb=fire_adapter.memory_mb or 65.0
        )
        db.add(fire_model)
        models.append(fire_model)

    # 7. Aegis Weapon & Dangerous Object Detector
    if "Aegis-Guard Dangerous Object & Weapon Detector" not in existing_names:
        weapon_adapter = perception_orchestrator.weapon_adapter
        weapon_status = AIModelStatus.LOADED if weapon_adapter.is_loaded else AIModelStatus.STANDBY
        weapon_model = AIModel(
            name="Aegis-Guard Dangerous Object & Weapon Detector",
            version="1.5.0",
            task=AIModelTask.WEAPON_DETECTION,
            provider="Specialized Security ONNX Model",
            model_path="data/models/weapon_detection_yolo.onnx",
            format="ONNX (.onnx)",
            input_resolution="640x640",
            classes_json=json.dumps(["handgun", "rifle", "knife", "bladed_weapon", "dangerous_package"]),
            device=weapon_adapter.device,
            status=weapon_status,
            inference_latency_ms=weapon_adapter.latency_ms or 0.0,
            inference_fps=weapon_adapter.fps or 0.0,
            memory_mb=weapon_adapter.memory_mb or 80.0
        )
        db.add(weapon_model)
        models.append(weapon_model)

    # 8. Crowd Intelligence Engine
    if "Crowd Intelligence & Spatial Density Engine" not in existing_names:
        crowd_adapter = perception_orchestrator.crowd_analyzer
        crowd_model = AIModel(
            name="Crowd Intelligence & Spatial Density Engine",
            version="2.0.0",
            task=AIModelTask.CROWD_ANALYSIS,
            provider="ARC-VISION Spatial Analytics",
            model_path="app/services/ai/perception/crowd_analyzer.py",
            format="Spatial Density Engine",
            input_resolution="Multi-Track Spatial Coordinates",
            classes_json=json.dumps(["crowd_formation", "density_threshold_breach", "rapid_surge"]),
            device="CPU",
            status=AIModelStatus.LOADED,
            inference_latency_ms=crowd_adapter.latency_ms or 0.5,
            inference_fps=200.0,
            memory_mb=crowd_adapter.memory_mb or 5.0
        )
        db.add(crowd_model)
        models.append(crowd_model)

    # 9. DeepAction Neural Action Transformer
    if "DeepAction Neural Action Transformer" not in existing_names:
        ml_action_model = AIModel(
            name="DeepAction Neural Action Transformer",
            version="1.2.0",
            task=AIModelTask.ACTION_RECOGNITION,
            provider="Spatial-Temporal Video Transformer",
            model_path="data/models/deepaction_vit_base.onnx",
            format="ONNX (.onnx)",
            input_resolution="224x224x16_frames",
            classes_json=json.dumps(["walking", "running", "falling", "fighting", "jumping", "crouching", "climbing"]),
            device="CPU",
            status=AIModelStatus.STANDBY,
            inference_latency_ms=0.0,
            inference_fps=0.0,
            memory_mb=0.0
        )
        db.add(ml_action_model)
        models.append(ml_action_model)

    # 10. Spectra Attribute Classifier
    if "Spectra-Attribute Vision Classifier" not in existing_names:
        attr_model = AIModel(
            name="Spectra-Attribute Vision Classifier",
            version="1.0.0",
            task=AIModelTask.ATTRIBUTE_ANALYSIS,
            provider="Multi-Task Attribute Classifier",
            model_path="data/models/person_vehicle_attributes.onnx",
            format="ONNX (.onnx)",
            input_resolution="256x128",
            classes_json=json.dumps(["upper_clothing_color", "lower_clothing_color", "helmet", "safety_vest", "backpack", "vehicle_color", "vehicle_type"]),
            device="CPU",
            status=AIModelStatus.STANDBY,
            inference_latency_ms=0.0,
            inference_fps=0.0,
            memory_mb=0.0
        )
        db.add(attr_model)
        models.append(attr_model)

    # 11. Behavior Analytics Intelligence Engine
    if "Behavior Analytics Intelligence Engine" not in existing_names:
        behavior_model = AIModel(
            name="Behavior Analytics Intelligence Engine",
            version="2.0.0",
            task=AIModelTask.BEHAVIOR,
            provider="ARC-VISION Kinematics Engine",
            model_path="app/services/analytics/behavior",
            format="Rule & Kinematics Engine",
            input_resolution="Multi-Track Vector History",
            classes_json=json.dumps([
                "loitering", "stationary_vehicle", "stationary_object", "wrong_way",
                "restricted_zone", "night_movement", "crowd_density", "abandoned_object",
                "removed_object", "repeated_movement", "rapid_movement", "suspicious_route"
            ]),
            device="CPU",
            status=AIModelStatus.LOADED,
            inference_latency_ms=1.2,
            inference_fps=120.0,
            memory_mb=12.0
        )
        db.add(behavior_model)
        models.append(behavior_model)

    await db.commit()
    for m in models:
        await db.refresh(m)
    return models

@router.get("/telemetry", response_model=PerceptionTelemetryResponse)
async def get_perception_telemetry():
    """Returns real-time system CPU, process memory, and all active AI model metrics."""
    return perception_orchestrator.get_system_telemetry()

@router.post("/{model_id}/reload", response_model=AIModelResponse)
async def reload_ai_model(
    model_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.OPERATOR]:
        raise HTTPException(status_code=403, detail="Only Admins and Operators can reload AI models")

    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    m = result.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    # Match adapter and invoke load
    for task, adapter in perception_orchestrator._adapters.items():
        if adapter.name == m.name or task.value == m.task.value:
            adapter.load()
            m.status = AIModelStatus.LOADED if adapter.is_loaded else AIModelStatus.STANDBY
            m.memory_mb = adapter.memory_mb
            break

    # Audit log
    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value,
        action="RELOAD_AI_MODEL",
        resource_type="AIModel",
        resource_id=str(m.id),
        details_json=json.dumps({"model_name": m.name, "status": m.status.value}),
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(m)
    return m

@router.post("/{model_id}/unload", response_model=AIModelResponse)
async def unload_ai_model(
    model_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.OPERATOR]:
        raise HTTPException(status_code=403, detail="Only Admins and Operators can unload AI models")

    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    m = result.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    for task, adapter in perception_orchestrator._adapters.items():
        if adapter.name == m.name or task.value == m.task.value:
            adapter.unload()
            m.status = AIModelStatus.STANDBY
            m.memory_mb = 0.0
            break

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value,
        action="UNLOAD_AI_MODEL",
        resource_type="AIModel",
        resource_id=str(m.id),
        details_json=json.dumps({"model_name": m.name}),
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(m)
    return m

# Camera AI Profiles Endpoints
@router.get("/camera-profiles", response_model=List[CameraAIProfileResponse])
async def list_camera_ai_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CameraAIProfile).order_by(CameraAIProfile.camera_id))
    profiles = list(result.scalars().all())
    
    # Ensure default profiles exist for all existing cameras
    cam_result = await db.execute(select(Camera.id))
    camera_ids = [r[0] for r in cam_result.all()]
    existing_cam_ids = {p.camera_id for p in profiles}

    for cid in camera_ids:
        if cid not in existing_cam_ids:
            new_p = CameraAIProfile(camera_id=cid)
            db.add(new_p)
            profiles.append(new_p)

    if len(profiles) > len(existing_cam_ids):
        await db.commit()
        for p in profiles:
            await db.refresh(p)

    return profiles

@router.get("/camera-profiles/{camera_id}", response_model=CameraAIProfileResponse)
async def get_camera_ai_profile(camera_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CameraAIProfile).where(CameraAIProfile.camera_id == camera_id))
    profile = result.scalars().first()
    if not profile:
        # Auto-create default
        profile = CameraAIProfile(camera_id=camera_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile

@router.put("/camera-profiles/{camera_id}", response_model=CameraAIProfileResponse)
async def update_camera_ai_profile(
    camera_id: int,
    data: CameraAIProfileUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.OPERATOR]:
        raise HTTPException(status_code=403, detail="Viewer role cannot modify Camera AI profiles")

    result = await db.execute(select(CameraAIProfile).where(CameraAIProfile.camera_id == camera_id))
    profile = result.scalars().first()
    if not profile:
        profile = CameraAIProfile(camera_id=camera_id)
        db.add(profile)

    update_dict = data.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(profile, k, v)

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value,
        action="UPDATE_CAMERA_AI_PROFILE",
        resource_type="CameraAIProfile",
        resource_id=str(camera_id),
        details_json=json.dumps(update_dict),
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/simulate-perception")
async def simulate_perception_event(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Dry-run simulation endpoint for testing specialized perception model events.
    """
    event_type = payload.get("event_type", "FALL_DETECTED")
    camera_id = payload.get("camera_id", 1)
    track_id = payload.get("track_id", 101)
    
    if event_type == "FALL_DETECTED":
        class MockDet:
            class_name = "person"
            track_id = track_id
            box = [0.2, 0.6, 0.7, 0.8]  # Prone aspect ratio: (0.7-0.2)/(0.8-0.6) = 0.5/0.2 = 2.5
            attributes = {"trajectory": [(0.45, 0.5), (0.45, 0.7)], "speed": 0.001}
        
        det_res = perception_orchestrator.fall_detector.evaluate_fall(MockDet(), current_time=time.time())
        # If persistence needed, simulate next step
        if not det_res:
            det_res = perception_orchestrator.fall_detector.evaluate_fall(MockDet(), current_time=time.time() + 3.0)
        return {"status": "SUCCESS", "simulated_event": det_res}

    elif event_type == "CROWD_DENSITY":
        zones = payload.get("zones", [{"id": 1, "name": "Plaza Area", "polygon": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}]}])
        persons = []
        for i in range(payload.get("count", 10)):
            class MockP:
                class_name = "person"
                track_id = i + 1
                attributes = {"centroid": (0.3 + (i % 3) * 0.1, 0.3 + (i // 3) * 0.1)}
            persons.append(MockP())
        
        evts = perception_orchestrator.crowd_analyzer.analyze_crowd(
            camera_id=camera_id,
            tracked_persons=persons,
            zones=zones,
            threshold=8,
            current_time=time.time()
        )
        if not evts:
            evts = perception_orchestrator.crowd_analyzer.analyze_crowd(
                camera_id=camera_id,
                tracked_persons=persons,
                zones=zones,
                threshold=8,
                current_time=time.time() + 6.0
            )
        return {"status": "SUCCESS", "simulated_events": evts}

    return {"status": "UNSUPPORTED_SIMULATION_EVENT", "event_type": event_type}
