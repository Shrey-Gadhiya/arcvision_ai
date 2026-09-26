# ARC VISION — Benchmarking & Telemetry Profiler

## 1. Running the Automated Profiler

The platform includes a deterministic benchmarking tool that evaluates single-frame detection latency, tracking latency, spatial rule evaluation, and end-to-end pipeline throughput.

```bash
cd backend
python tests/benchmark_pipeline.py
```

---

## 2. Machine-Readable Telemetry Outputs
The benchmark outputs real execution measurements to `backend/data/benchmarks/benchmark_report.json`:

```json
{
  "timestamp": "2026-09-26T13:57:46Z",
  "model_loaded": "yolov8n_openvino_model",
  "model_load_latency_ms": 8.12,
  "frame_resolution": "1280x720",
  "cycles": 50,
  "detection_latency": {
    "mean_ms": 189.3,
    "p95_ms": 233.0,
    "min_ms": 164.2,
    "max_ms": 258.1
  },
  "tracking_latency": {
    "mean_ms": 0.01,
    "p95_ms": 0.01
  },
  "spatial_rule_latency": {
    "mean_ms": 0.0,
    "p95_ms": 0.0
  },
  "end_to_end_single_frame_latency_ms": 189.3,
  "estimated_peak_throughput_fps": 5.28
}
```

*Note: On CUDA/TensorRT GPU hardware (e.g. RTX 4090 / A100), detection latency is typically 3–8 ms per frame, enabling 120+ FPS throughput.*
