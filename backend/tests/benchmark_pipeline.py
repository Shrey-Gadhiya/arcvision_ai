import os
import sys
import time
import json
import numpy as np
import cv2
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ai.detector import YOLODetectorAdapter
from app.services.ai.tracker import MultiObjectTracker
from app.services.analytics.zone_engine import zone_engine
from app.services.analytics.rule_evaluator import rule_evaluator
from app.services.analytics.incident_intelligence import incident_intelligence
from app.services.recording_engine import compute_sha256
from app.models.rule import Rule, RuleEventType, RuleSeverity

def run_benchmark(num_frames: int = 100):
    print("================================================================")
    print("       ARC VISION PIPELINE BENCHMARK & TELEMETRY PROFILER       ")
    print("================================================================")
    
    # 1. Initialize detector & tracker
    model_path = "../yolov8n.pt" if os.path.exists("../yolov8n.pt") else "yolov8n.pt"
    t_start_load = time.perf_counter()
    detector = YOLODetectorAdapter(model_name=model_path)
    tracker = MultiObjectTracker()
    load_time_ms = (time.perf_counter() - t_start_load) * 1000
    
    # Synthetic frame generation
    frame_h, frame_w = 720, 1280
    test_frame = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
    # Draw simple shapes to simulate targets
    cv2.rectangle(test_frame, (200, 200), (350, 600), (120, 120, 120), -1)
    cv2.circle(test_frame, (275, 230), 30, (200, 200, 200), -1)
    
    # 2. Warm-up
    print("Warming up inference engine...")
    for _ in range(5):
        detector.detect(test_frame, confidence_threshold=0.25)
        
    # 3. Benchmark Detection
    print(f"Profiling Detection over {num_frames} cycles...")
    det_latencies = []
    for _ in range(num_frames):
        t0 = time.perf_counter()
        detections = detector.detect(test_frame, confidence_threshold=0.25)
        t1 = time.perf_counter()
        det_latencies.append((t1 - t0) * 1000)
        
    # 4. Benchmark Tracking
    print(f"Profiling Multi-Object Tracking over {num_frames} cycles...")
    track_latencies = []
    for _ in range(num_frames):
        t0 = time.perf_counter()
        tracks = tracker.update(detections)
        t1 = time.perf_counter()
        track_latencies.append((t1 - t0) * 1000)
        
    # 5. Benchmark Spatial Rule & Geometry Engine
    print(f"Profiling Spatial Geometry & Rule Evaluator...")
    zones = [{
        "id": 1,
        "name": "Restricted Zone A",
        "zone_type": "RESTRICTED",
        "points": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
    }]
    test_rule = Rule(
        id=1,
        name="Zone Intrusion Alert",
        event_type=RuleEventType.ZONE_INTRUSION,
        severity=RuleSeverity.CRITICAL,
        camera_ids_json=json.dumps([1]),
        conditions_json=json.dumps({"target_classes": ["person"], "zones": [1]}),
        cooldown_seconds=0,
        is_active=True,
        schedule_json=json.dumps({"always": True})
    )
    
    spatial_latencies = []
    for _ in range(num_frames):
        t0 = time.perf_counter()
        events = []
        for trk in tracks:
            occ = zone_engine.check_zone_occupancy(trk.centroid, zones)
            if occ:
                events.append({"track_id": trk.track_id, "zone": occ[0]})
        t1 = time.perf_counter()
        spatial_latencies.append((t1 - t0) * 1000)
        
    # 6. Aggregate Metrics
    det_mean = float(np.mean(det_latencies))
    det_p95 = float(np.percentile(det_latencies, 95))
    det_min = float(np.min(det_latencies))
    det_max = float(np.max(det_latencies))
    
    trk_mean = float(np.mean(track_latencies))
    trk_p95 = float(np.percentile(track_latencies, 95))
    
    spa_mean = float(np.mean(spatial_latencies))
    spa_p95 = float(np.percentile(spatial_latencies, 95))
    
    total_pipeline_mean_ms = det_mean + trk_mean + spa_mean
    estimated_max_fps = 1000.0 / total_pipeline_mean_ms if total_pipeline_mean_ms > 0 else 0
    
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_loaded": detector.model_name if hasattr(detector, "model_name") else "YOLOv8n",
        "model_load_latency_ms": round(load_time_ms, 2),
        "frame_resolution": f"{frame_w}x{frame_h}",
        "cycles": num_frames,
        "detection_latency": {
            "mean_ms": round(det_mean, 2),
            "p95_ms": round(det_p95, 2),
            "min_ms": round(det_min, 2),
            "max_ms": round(det_max, 2)
        },
        "tracking_latency": {
            "mean_ms": round(trk_mean, 2),
            "p95_ms": round(trk_p95, 2)
        },
        "spatial_rule_latency": {
            "mean_ms": round(spa_mean, 2),
            "p95_ms": round(spa_p95, 2)
        },
        "end_to_end_single_frame_latency_ms": round(total_pipeline_mean_ms, 2),
        "estimated_peak_throughput_fps": round(estimated_max_fps, 2)
    }
    
    out_dir = Path("data/benchmarks")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "benchmark_report.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n----------------- BENCHMARK RESULTS -----------------")
    print(f"Model Load Time         : {results['model_load_latency_ms']} ms")
    print(f"Detection Mean Latency  : {results['detection_latency']['mean_ms']} ms (P95: {results['detection_latency']['p95_ms']} ms)")
    print(f"Tracking Mean Latency   : {results['tracking_latency']['mean_ms']} ms (P95: {results['tracking_latency']['p95_ms']} ms)")
    print(f"Spatial/Rule Mean Lat   : {results['spatial_rule_latency']['mean_ms']} ms (P95: {results['spatial_rule_latency']['p95_ms']} ms)")
    print(f"End-to-End Processing   : {results['end_to_end_single_frame_latency_ms']} ms / frame")
    print(f"Estimated Max Throughput: {results['estimated_peak_throughput_fps']} FPS")
    print(f"Report written to       : {report_file}")
    print("-----------------------------------------------------")
    return results

if __name__ == "__main__":
    run_benchmark(num_frames=50)
