# ARC VISION — AI Model Catalog & Perception Ecosystem

## 1. Primary Model Architecture & Selection Matrix

| Model Tier | Candidate Architectures | Recommended Deployment | Runtime Acceleration | Task Domain |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Balanced** | YOLO26m / YOLOv8m / YOLO11m | Medium-to-large multi-camera sectors | TensorRT FP16 / OpenVINO / CUDA | Perimeter Target Detection (Persons, Vehicles, Bags) |
| **Fast Edge** | YOLO26s / YOLO26n / YOLOv8n | High stream count (16–64 cameras) | TensorRT INT8 / OpenVINO CPU | Lightweight continuous motion monitoring |
| **Deep Forensic** | YOLO26l / YOLO26x / YOLOv8x | Critical intrusion verification | TensorRT FP16 / PyTorch CUDA | High-confidence threat analysis & small-target isolation |
| **Pose & Kinematics** | YOLO26-Pose / YOLOv8-Pose | Sector fences & restricted zones | TensorRT / ONNX Runtime | Climbing, crouching, falling, posture anomaly |
| **Promptable Segmentation**| SAM-Forensic / YOLO26-Seg / FastSAM | Forensic Dossier / Investigation | TensorRT / ONNX CUDA | Pixel-accurate object mask & crowd boundary extraction |
| **Open-Vocabulary** | YOLOE-26 / CLIP-guided ViT | Deep investigation search | ONNX Runtime CUDA | Natural language query ("weapon", "ladder", "gear") |
| **Monocular Depth** | Depth-Anything-V2 Small/Base | Perimeter 3D penetration | ONNX Runtime / OpenVINO | Distance estimation & 3D trajectory tracking |
| **Biometric Face** | ResNet-10 DNN / ArcFace / InsightFace | Checkpoints & access gates | OpenVINO / TensorRT | 512-d biometric embedding & watchlist matching |
| **License Plate OCR**| EasyOCR / CRNN / PaddleOCR | Border checkposts & road corridors | CUDA / PyTorch / OpenVINO | Vehicle license plate localization & temporal consensus |

---

## 2. Model Evaluation & Hardware Suitability Analysis

### YOLO26m vs Alternatives
- **Why YOLO26m is the Primary Candidate**: Offers an optimal balance of mean average precision (mAP 51.5+ on COCO), sub-10ms inference on modern CUDA GPUs, native TensorRT/OpenVINO export support, and robust small-object detection in outdoor perimeter scenes.
- **Why YOLO26x is Not Used on Every Frame**: While YOLO26x achieves higher mAP, its 3x memory footprint and higher inference latency would exhaust GPU VRAM when multiplexing 16+ high-definition RTSP streams. It is reserved for the **DEEP PATH**.
- **Model Agnostic Hot-Swapping**: The platform decouples model loading through `DetectorRegistry`, allowing operators to switch active model weights via configuration without restarting services.
