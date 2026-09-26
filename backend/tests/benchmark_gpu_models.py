import os
import sys
import time
import json
from pathlib import Path
import numpy as np
import cv2
import torch
import psutil

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ai.detector import YOLODetectorAdapter
from app.services.ai.face.adapters import YuNetFaceDetectorAdapter, SFaceEmbeddingAdapter
from app.services.ai.perception.orchestrator import perception_orchestrator
from app.services.ai.router import ai_router
from app.services.ai.tensorrt_builder import tensorrt_builder

def calc_stats(latencies: list) -> dict:
    if not latencies:
        return {"p50_ms": 0.0, "p90_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "mean_ms": 0.0, "fps": 0.0}
    mean = float(np.mean(latencies))
    return {
        "p50_ms": round(float(np.percentile(latencies, 50)), 2),
        "p90_ms": round(float(np.percentile(latencies, 90)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "p99_ms": round(float(np.percentile(latencies, 99)), 2),
        "mean_ms": round(mean, 2),
        "fps": round(1000.0 / max(0.001, mean), 2),
        "min_ms": round(float(np.min(latencies)), 2),
        "max_ms": round(float(np.max(latencies)), 2)
    }

def run_real_model_benchmark(num_cycles: int = 30):
    print("=================================================================")
    print("       ARC VISION REAL AI MODEL HARDWARE BENCHMARK SUITE         ")
    print("=================================================================")
    
    hw = ai_router.get_hardware_status()
    trt_avail, trt_msg = tensorrt_builder.is_tensorrt_available()
    
    print(f"CUDA Available      : {hw['gpu_available']} (Devices: {hw['gpu_count']})")
    print(f"TensorRT Status     : {trt_avail} ({trt_msg})")
    print(f"System RAM In-Use   : {hw['process_ram_mb']} MB")
    print(f"CPU Utilization     : {hw['cpu_utilization_pct']} %")
    print("-----------------------------------------------------------------")
    
    test_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.rectangle(test_img, (300, 200), (500, 600), (140, 140, 140), -1)
    cv2.circle(test_img, (400, 260), 45, (220, 220, 220), -1)
    
    results = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "cuda_available": hw['gpu_available'],
            "gpu_count": hw['gpu_count'],
            "tensorrt_status": trt_msg,
            "pytorch_version": torch.__version__,
            "cpu_threads": psutil.cpu_count(logical=True)
        },
        "models_evaluated": {}
    }
    
    # 1. Primary Detector: YOLO26m / OpenVINO / CPU
    print("\n[1/3] Benchmarking Primary Object Detector (YOLO26m / OpenVINO / CPU)...")
    model_path = "../yolov8n.pt" if os.path.exists("../yolov8n.pt") else "yolov8n.pt"
    t_load0 = time.perf_counter()
    detector = YOLODetectorAdapter(name="YOLO26m Primary Detector", model_path=model_path)
    t_load_ms = (time.perf_counter() - t_load0) * 1000.0
    
    # Warmup
    for _ in range(3):
        detector.detect(test_img, confidence_threshold=0.25)
        
    yolo_latencies = []
    for _ in range(num_cycles):
        t0 = time.perf_counter()
        _ = detector.detect(test_img, confidence_threshold=0.25)
        t1 = time.perf_counter()
        yolo_latencies.append((t1 - t0) * 1000.0)
        
    yolo_stats = calc_stats(yolo_latencies)
    results["models_evaluated"]["yolo26m_primary_detector"] = {
        "status": "MEASURED",
        "runtime": detector.runtime,
        "device": detector.device,
        "precision": detector.precision,
        "load_time_ms": round(t_load_ms, 2),
        "cycles": num_cycles,
        "latency_stats": yolo_stats
    }
    print(f" -> YOLO26m Mean: {yolo_stats['mean_ms']} ms | P95: {yolo_stats['p95_ms']} ms | FPS: {yolo_stats['fps']}")
    
    # 2. Modern Face Detector (YuNet ONNX)
    print("\n[2/3] Benchmarking YuNet Face Detector ONNX...")
    yunet = YuNetFaceDetectorAdapter()
    yunet_loaded = yunet.load()
    if yunet_loaded:
        for _ in range(3):
            yunet.detect_faces(test_img)
        yunet_lats = []
        for _ in range(num_cycles):
            t0 = time.perf_counter()
            _ = yunet.detect_faces(test_img)
            t1 = time.perf_counter()
            yunet_lats.append((t1 - t0) * 1000.0)
        yunet_stats = calc_stats(yunet_lats)
        results["models_evaluated"]["face_detector_yunet"] = {
            "status": "MEASURED",
            "runtime": "OpenCV_DNN_ONNX",
            "device": yunet.device,
            "cycles": num_cycles,
            "latency_stats": yunet_stats
        }
        print(f" -> YuNet Mean: {yunet_stats['mean_ms']} ms | P95: {yunet_stats['p95_ms']} ms | FPS: {yunet_stats['fps']}")
    else:
        results["models_evaluated"]["face_detector_yunet"] = {
            "status": "NOT_DEPLOYED",
            "reason": yunet.last_error
        }
        print(f" -> YuNet: NOT DEPLOYED ({yunet.last_error})")
        
    # 3. Modern Face Embedding (SFace ONNX)
    print("\n[3/3] Benchmarking SFace Face Recognition ONNX...")
    sface = SFaceEmbeddingAdapter()
    sface_loaded = sface.load()
    if sface_loaded:
        face_crop = np.zeros((112, 112, 3), dtype=np.uint8)
        for _ in range(3):
            sface.compute_embedding(face_crop)
        sface_lats = []
        for _ in range(num_cycles):
            t0 = time.perf_counter()
            _ = sface.compute_embedding(face_crop)
            t1 = time.perf_counter()
            sface_lats.append((t1 - t0) * 1000.0)
        sface_stats = calc_stats(sface_lats)
        results["models_evaluated"]["face_embedding_sface"] = {
            "status": "MEASURED",
            "runtime": "OpenCV_DNN_ONNX",
            "device": sface.device,
            "cycles": num_cycles,
            "latency_stats": sface_stats
        }
        print(f" -> SFace Mean: {sface_stats['mean_ms']} ms | P95: {sface_stats['p95_ms']} ms | FPS: {sface_stats['fps']}")
    else:
        results["models_evaluated"]["face_embedding_sface"] = {
            "status": "NOT_DEPLOYED",
            "reason": sface.last_error
        }
        print(f" -> SFace: NOT DEPLOYED ({sface.last_error})")

    # Output machine-readable benchmark report
    out_dir = Path("data/benchmarks")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "gpu_models_benchmark.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n-----------------------------------------------------------------")
    print(f"Hardware & Model Benchmark successfully written to: {report_path}")
    print("=================================================================")
    return results

if __name__ == "__main__":
    run_real_model_benchmark(num_cycles=25)
