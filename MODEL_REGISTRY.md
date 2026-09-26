# ARC VISION — Model Registry & Perception Architecture

## 1. Deployed & Verified Models in ARC VISION

| Subsystem / Role | Model Family & Architecture | Artifact Path | Parameters | SHA-256 Hash | Active Runtime | Verified Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Perimeter Detector** | YOLOv8m (Ultralytics) | `data/models/detection/yolov8m/yolov8m.pt` | 25,902,640 | `233ae2ebad7d0...` | PyTorch / OpenVINO | `VERIFIED / ACTIVE` |
| **Fast-Path Edge Detector** | YOLOv8s (Ultralytics) | `data/models/detection/yolov8s/yolov8s.pt` | 11,166,560 | `00155a004f2cf...` | PyTorch / OpenVINO | `VERIFIED / ACTIVE` |
| **Deep Forensic Detector** | YOLOv8l (Ultralytics) | `data/models/detection/yolov8l/yolov8l.pt` | 43,691,520 | `e58b9f0be8930...` | PyTorch / OpenVINO | `VERIFIED / STANDBY` |
| **Fallback Perimeter Detector** | YOLOv8n (Ultralytics) | `yolov8n.pt` / `yolov8n_openvino_model/` | 3,157,200 | `f59b3d833e2ff...` | OpenVINO FP16 | `VERIFIED / FALLBACK` |
| **Tactical Pose (17-Keypoint)** | YOLOv8n-Pose (Ultralytics) | `data/models/pose/yolov8n-pose.pt` | 3,295,470 | `c40f5a7a72d73...` | PyTorch / CPU | `VERIFIED / ACTIVE` |
| **Forensic Segmentation** | YOLOv8n-Seg (Ultralytics) | `data/models/segmentation/yolov8n-seg.pt` | 3,409,968 | `36511a37c0500...` | PyTorch / CPU | `VERIFIED / STANDBY` |
| **Modern Face Detector** | YuNet (OpenCV Model Zoo) | `data/models/face_detection_yunet_2023mar.onnx`| 85,000 | `8f2383e4dd3cf...` | OpenCV DNN CPU | `VERIFIED / ACTIVE` |
| **Modern Face Recognition** | SFace MobileFaceNet | `data/models/face_recognition_sface_2021dec.onnx`| 1,800,000 | `e5bc418a09f87...` | OpenCV DNN CPU | `VERIFIED / ACTIVE` |
| **ANPR / Plate OCR Engine** | Indian ALPR Normalizer + Regex | Native Service | Heuristic | N/A | Python CPU | `VERIFIED / ACTIVE` |
| **Cross-Camera Re-ID** | Biometric & Plate Fusion Graph | Multi-Modal Tracker | Spatial-Temporal | N/A | Python CPU | `VERIFIED / ACTIVE` |
| **Monocular Depth Engine** | Perspective Depth Engine | Native Geometry Adapter | Geometric | N/A | Python CPU | `STANDBY / RELATIVE` |
| **Open-Vocabulary Adapter** | Surveillance Lexicon Adapter | Heuristic Text Search | Lexicon Index | N/A | Python CPU | `STANDBY / HEURISTIC` |
| **Behavior Analytics Engine** | 11 Kinematic Analytics Rules | Real-Time Vector Engine | Rule Engine | N/A | Python CPU | `VERIFIED / ACTIVE` |

---

## 2. Managing Models with Setup Tools

### Automated Model Acquisition & Verification
```bash
# Acquire all official models
python scripts/setup_models.py --all

# Acquire specific subsystems
python scripts/setup_models.py --detectors
python scripts/setup_models.py --pose
python scripts/setup_models.py --seg
```

### Checking Real Runtime Model Status
```bash
python scripts/model_status.py
```
