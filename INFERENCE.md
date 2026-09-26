# ARC VISION — GPU Inference Fabric & Adaptive Compute Engine

## 1. Fast Path vs Deep Path Adaptive Routing

To prevent GPU compute exhaustion and minimize latency across dozens of CCTV feeds, ARC VISION partitions frame processing into two distinct execution lanes:

```
                            Camera Video Stream
                                     │
                             [ Motion Gating ]
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
              [ FAST PATH ]                     [ DEEP PATH ]
        (Continuous Surveillance)          (Triggered by Intrusion / Rule)
                    │                                 │
           YOLO26m / YOLO26s                  YOLO26l / YOLO26x
                    │                                 │
           Multi-Object Tracker                 Pose Estimation
                    │                                 │
           Spatial Rule Check                  SAM / Segmentation
                    │                                 │
            Incident Trigger ────────────────► Open-Vocabulary Query
                                                      │
                                               Cross-Camera Re-ID
```

---

## 2. Hardware Acceleration Fallback Hierarchy

The system automatically detects available hardware compute and configures execution:

$$\text{TensorRT FP16 (NVIDIA GPU)} \longrightarrow \text{ONNX Runtime CUDA} \longrightarrow \text{OpenVINO (Intel/AMD CPU)} \longrightarrow \text{PyTorch CPU Fallback}$$

1. **TensorRT**: Compiled engine plans with FP16 half-precision, achieving 120+ FPS per GPU worker.
2. **ONNX Runtime (CUDA Execution Provider)**: Direct GPU execution with dynamic input tensor shapes.
3. **OpenVINO**: Optimized CPU graph execution using AVX-512 / VNNI instruction sets for edge deployments.
4. **PyTorch CPU**: Resilient baseline fallback ensuring zero downtime when GPU hardware is unavailable.
