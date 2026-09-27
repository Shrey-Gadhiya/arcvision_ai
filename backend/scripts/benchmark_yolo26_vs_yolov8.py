import time
import statistics
import os
from pathlib import Path
import numpy as np
import torch
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS = BACKEND_DIR / "data" / "models"
YOLO26_DIR = DATA_MODELS / "detection" / "yolo26"
YOLO8_DIR = DATA_MODELS / "detection"

def benchmark_model(model_path: Path, name: str, device: str = "cuda:0", precision: str = "fp16", iterations: int = 30, warmup: int = 8):
    if not model_path.exists():
        return None
    
    try:
        model = YOLO(str(model_path))
        if device.startswith("cuda") and torch.cuda.is_available():
            model.to(device)
            use_half = (precision == "fp16")
        else:
            device = "cpu"
            use_half = False

        # Synthetic 640x640 frame
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        
        # Warmup
        for _ in range(warmup):
            _ = model(img, device=device, verbose=False)
        if str(device).startswith("cuda"):
            torch.cuda.synchronize()
            
        latencies = []
        for _ in range(iterations):
            if str(device).startswith("cuda"):
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            _ = model(img, device=device, verbose=False)
            if str(device).startswith("cuda"):
                torch.cuda.synchronize()
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms
            
        mean_lat = statistics.mean(latencies)
        median_lat = statistics.median(latencies)
        sorted_lat = sorted(latencies)
        p95_lat = sorted_lat[int(len(sorted_lat) * 0.95)]
        p99_lat = sorted_lat[int(len(sorted_lat) * 0.99)]
        fps = 1000.0 / mean_lat if mean_lat > 0 else 0.0
        params = sum(p.numel() for p in model.model.parameters())
        
        return {
            "name": name,
            "path": str(model_path.name),
            "device": device.upper(),
            "precision": "FP16" if use_half else "FP32",
            "params_m": round(params / 1e6, 2),
            "mean_ms": round(mean_lat, 2),
            "median_ms": round(median_lat, 2),
            "p95_ms": round(p95_lat, 2),
            "p99_ms": round(p99_lat, 2),
            "fps": round(fps, 1)
        }
    except Exception as e:
        print(f"Error benchmarking {name}: {e}")
        return None

def main():
    gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
    target_device = "cuda:0" if gpu_count > 0 else "cpu"
    precision = "fp16" if gpu_count > 0 else "fp32"
    
    print("=" * 95)
    print("  ARC VISION - HIGH-PERFORMANCE AI INFERENCE BENCHMARK  ")
    print(f"  Hardware: {gpu_count}x NVIDIA GPU(s) Detected | Active Target: {target_device.upper()} ({precision.upper()})")
    for i in range(gpu_count):
        print(f"    - GPU {i}: {torch.cuda.get_device_name(i)} ({round(torch.cuda.get_device_properties(i).total_memory / 1024**3, 1)} GB VRAM)")
    print("=" * 95)
    
    models = [
        (YOLO26_DIR / "yolo26s.pt", "YOLO26s (Fast Path)"),
        (YOLO8_DIR / "yolov8s" / "yolov8s.pt", "YOLOv8s (Fallback Fast)"),
        (YOLO26_DIR / "yolo26m.pt", "YOLO26m (Primary Detector)"),
        (YOLO8_DIR / "yolov8m" / "yolov8m.pt", "YOLOv8m (Fallback Primary)"),
        (YOLO26_DIR / "yolo26l.pt", "YOLO26l (Deep Forensic)"),
        (YOLO8_DIR / "yolov8l" / "yolov8l.pt", "YOLOv8l (Fallback Deep)"),
        (YOLO26_DIR / "yolo26x.pt", "YOLO26x (Extreme Forensic)"),
    ]
    
    results = []
    for path, name in models:
        if path.exists():
            print(f"Benchmarking {name} on {target_device.upper()}...")
            res = benchmark_model(path, name, device=target_device, precision=precision, iterations=25, warmup=5)
            if res:
                results.append(res)
                print(f"  -> Latency: {res['mean_ms']}ms | Throughput Capacity: {res['fps']} FPS")

    print("\n" + "=" * 105)
    print(f"{'MODEL':<26} | {'DEVICE':<8} | {'PRECISION':<9} | {'LATENCY (ms)':<13} | {'RAW COMPUTE (FPS)':<18} | {'CONCURRENT 30FPS CAMS':<20}")
    print("-" * 105)
    for r in results:
        max_cams = int(r['fps'] / 30.0)
        multi_gpu_cams = max_cams * max(1, gpu_count)
        print(f"{r['name']:<26} | {r['device']:<8} | {r['precision']:<9} | {r['mean_ms']:>11.2f} ms | {r['fps']:>15.1f} FPS | ~{multi_gpu_cams} streams ({gpu_count}x GPU)")
    print("=" * 105)
    print(" NOTE: Live video streams are paced to their native 30 FPS for 1:1 real-time playback.")
    print(" Multi-GPU capacity allows running multiple simultaneous camera streams without frame drops.")
    print("=" * 105)

if __name__ == "__main__":
    main()

