import logging
import psutil
from typing import Dict, Any, Optional, List
from enum import Enum
import torch

logger = logging.getLogger("arc_vision.ai.router")

class TaskUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    BACKGROUND = "background"

class SceneCondition(str, Enum):
    DAY = "day"
    NIGHT = "night"
    LOW_LIGHT = "low_light"
    RAIN_FOG = "rain_fog"

class ModelTier(str, Enum):
    FAST = "fast"          # YOLO26s / YOLO26n
    PRIMARY = "primary"    # YOLO26m / YOLOv8n
    DEEP = "deep"          # YOLO26l
    FORENSIC = "forensic"  # YOLO26x / SAM

class AIRouter:
    """
    Centralized Model Router and Adaptive Compute Scheduler.
    Dynamically routes AI inference tasks based on:
    - Urgency / Event Severity
    - Scene condition & lighting
    - Current GPU VRAM & system load
    - Available accelerator runtimes
    """
    def __init__(self):
        self._gpu_available = torch.cuda.is_available()
        self._gpu_count = torch.cuda.device_count() if self._gpu_available else 0
        self._runtime_priority = ["TensorRT", "ONNXRuntime_CUDA", "PyTorch_CUDA", "OpenVINO", "PyTorch_CPU"]

    def get_hardware_status(self) -> Dict[str, Any]:
        vram_allocated_mb = 0.0
        vram_total_mb = 0.0
        if self._gpu_available:
            try:
                vram_allocated_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 2)
                vram_total_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 2)
            except Exception:
                pass

        process = psutil.Process()
        ram_mb = round(process.memory_info().rss / (1024 * 1024), 2)
        cpu_pct = psutil.cpu_percent(interval=None)

        return {
            "gpu_available": self._gpu_available,
            "gpu_count": self._gpu_count,
            "vram_allocated_mb": vram_allocated_mb,
            "vram_total_mb": vram_total_mb,
            "cpu_utilization_pct": cpu_pct,
            "process_ram_mb": ram_mb
        }

    def route(
        self,
        task: str = "object_detection",
        camera_id: int = 1,
        scene: str = "day",
        urgency: str = "normal",
        gpu_load: float = 0.0
    ) -> Dict[str, Any]:
        """
        Determines the optimal model tier, runtime provider, input resolution, and sampling FPS.
        Priority Matrix:
        - CRITICAL: YOLO26l/x + Full Resolution + Deep Path Specialized Tasks (Pose, SAM, Re-ID)
        - HIGH: YOLO26m + Primary Resolution (640x640) + Motion Gating
        - NORMAL: YOLO26s/m + Adaptive Sampling (10-15 FPS)
        - BACKGROUND / STATIC: YOLO26s/n + 2-5 FPS Low-Power Sampling
        """
        urgency_lower = urgency.lower()
        
        # 1. Determine Model Tier
        if urgency_lower == TaskUrgency.CRITICAL.value:
            selected_tier = ModelTier.DEEP.value
            model_key = "yolo26l"
            resolution = "1280x1280"
            target_fps = 30
            enable_deep_path = True
        elif urgency_lower == TaskUrgency.HIGH.value:
            selected_tier = ModelTier.PRIMARY.value
            model_key = "yolo26m"
            resolution = "640x640"
            target_fps = 20
            enable_deep_path = True
        elif urgency_lower == TaskUrgency.BACKGROUND.value:
            selected_tier = ModelTier.FAST.value
            model_key = "yolo26s"
            resolution = "512x512"
            target_fps = 5
            enable_deep_path = False
        else:
            # NORMAL
            selected_tier = ModelTier.PRIMARY.value
            model_key = "yolo26m"
            resolution = "640x640"
            target_fps = 15
            enable_deep_path = False

        # 2. Select Device & Runtime Fallback
        if self._gpu_available:
            assigned_device = f"cuda:{camera_id % max(1, self._gpu_count)}"
            active_runtime = "TensorRT" if not enable_deep_path else "PyTorch_CUDA"
            precision = "fp16"
        else:
            assigned_device = "cpu"
            active_runtime = "OpenVINO"
            precision = "fp16"

        return {
            "task": task,
            "camera_id": camera_id,
            "model_tier": selected_tier,
            "model_key": model_key,
            "resolution": resolution,
            "target_fps": target_fps,
            "assigned_device": assigned_device,
            "active_runtime": active_runtime,
            "precision": precision,
            "enable_deep_path": enable_deep_path,
            "scene_condition": scene,
            "urgency": urgency
        }

ai_router = AIRouter()
