import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import torch

logger = logging.getLogger("arc_vision.ai.tensorrt_builder")

class TensorRTEngineBuilder:
    """
    TensorRT Engine Generation, Validation, and Compatibility Service.
    Automates the conversion pipeline: PyTorch (.pt) -> ONNX (.onnx) -> TensorRT FP16 (.engine).
    Performs safety verification and graceful fallback when TensorRT/CUDA is unavailable.
    """
    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir) if models_dir else Path(__file__).parent.parent.parent.parent / "data" / "models"

    def is_tensorrt_available(self) -> Tuple[bool, str]:
        """
        Checks if TensorRT python bindings and a CUDA-capable GPU are present.
        """
        if not torch.cuda.is_available():
            return False, "CUDA is not available in the current environment"
        try:
            import tensorrt as trt
            return True, f"TensorRT version {trt.__version__} available on {torch.cuda.get_device_name(0)}"
        except ImportError:
            return False, "tensorrt Python package is not installed"
        except Exception as e:
            return False, f"TensorRT initialization error: {str(e)}"

    def validate_engine(self, engine_path: str) -> Dict[str, Any]:
        """
        Verifies that an engine file exists, is non-empty, and has a verifiable hash.
        """
        p = Path(engine_path)
        if not p.exists():
            return {
                "valid": False,
                "reason": f"Engine file not found: {engine_path}",
                "sha256": None,
                "file_size_bytes": 0
            }

        size = p.stat().st_size
        if size < 1024:
            return {
                "valid": False,
                "reason": f"Engine file corrupted or truncated (size: {size} bytes)",
                "sha256": None,
                "file_size_bytes": size
            }

        # Compute SHA-256
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)

        return {
            "valid": True,
            "reason": "Engine file verified",
            "sha256": h.hexdigest(),
            "file_size_bytes": size
        }

    def build_engine_from_onnx(
        self,
        onnx_path: str,
        engine_path: str,
        precision: str = "fp16",
        max_batch_size: int = 1
    ) -> Dict[str, Any]:
        """
        Converts an ONNX model into a TensorRT optimized engine plan.
        """
        trt_avail, reason = self.is_tensorrt_available()
        if not trt_avail:
            logger.info(f"TensorRT build bypassed: {reason}. Operating in fallback mode.")
            return {
                "success": False,
                "reason": reason,
                "engine_path": None
            }

        try:
            import tensorrt as trt
            trt_logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(trt_logger)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, trt_logger)

            with open(onnx_path, "rb") as model_f:
                if not parser.parse(model_f.read()):
                    errors = [parser.get_error(i).desc() for i in range(parser.num_errors)]
                    return {"success": False, "reason": f"ONNX Parse Error: {errors}", "engine_path": None}

            config = builder.create_builder_config()
            if precision.lower() == "fp16" and builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)

            plan = builder.build_serialized_network(network, config)
            if plan is None:
                return {"success": False, "reason": "Failed to build serialized TensorRT engine plan", "engine_path": None}

            out_p = Path(engine_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "wb") as f:
                f.write(plan)

            logger.info(f"Successfully generated TensorRT engine at: {out_p}")
            return {
                "success": True,
                "reason": "Engine plan compiled successfully",
                "engine_path": str(out_p),
                "precision": precision
            }
        except Exception as e:
            logger.error(f"Failed to compile TensorRT engine: {e}")
            return {
                "success": False,
                "reason": str(e),
                "engine_path": None
            }

tensorrt_builder = TensorRTEngineBuilder()
