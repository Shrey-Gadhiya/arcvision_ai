import time
import statistics
from pathlib import Path
import numpy as np
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS = BACKEND_DIR / "data" / "models"
YOLO26_DIR = DATA_MODELS / "detection" / "yolo26"
YOLO8_DIR = DATA_MODELS / "detection"

def benchmark_model(model_path: Path, name: str, iterations: int = 15, warmup: int = 5):
    if not model_path.exists():
        return None
    
    try:
        model = YOLO(str(model_path))
        # synthetic 640x640 frame
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        
        # Warmup
        for _ in range(warmup):
            _ = model(img, verbose=False)
            
        latencies = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            _ = model(img, verbose=False)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0) # ms
            
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
    print("=" * 80)
    print("  ARC VISION - HONEST CPU BENCHMARK (YOLO26 vs YOLOv8)  ")
    print("  Platform: Windows x86_64, PyTorch CPU FP32, Input: 640x640  ")
    print("=" * 80)
    
    models = [
        (YOLO26_DIR / "yolo26s.pt", "YOLO26s (Fast)"),
        (YOLO8_DIR / "yolov8s" / "yolov8s.pt", "YOLOv8s (Fallback Fast)"),
        (YOLO26_DIR / "yolo26m.pt", "YOLO26m (Primary)"),
        (YOLO8_DIR / "yolov8m" / "yolov8m.pt", "YOLOv8m (Fallback Primary)"),
        (YOLO26_DIR / "yolo26l.pt", "YOLO26l (Deep Forensic)"),
        (YOLO8_DIR / "yolov8l" / "yolov8l.pt", "YOLOv8l (Fallback Deep)"),
        (YOLO26_DIR / "yolo26x.pt", "YOLO26x (Extreme Forensic)"),
    ]
    
    results = []
    for path, name in models:
        print(f"Benchmarking {name} on CPU...")
        res = benchmark_model(path, name, iterations=12, warmup=3)
        if res:
            results.append(res)
            print(f"  -> Mean: {res['mean_ms']}ms | P95: {res['p95_ms']}ms | FPS: {res['fps']}")

    print("\n" + "=" * 90)
    print(f"{'MODEL':<28} | {'PARAMS':<8} | {'MEAN (ms)':<10} | {'P95 (ms)':<10} | {'THROUGHPUT (FPS)':<16}")
    print("-" * 90)
    for r in results:
        print(f"{r['name']:<28} | {r['params_m']:>6.1f}M | {r['mean_ms']:>10.1f} | {r['p95_ms']:>10.1f} | {r['fps']:>16.1f}")
    print("=" * 90)

if __name__ == "__main__":
    main()
