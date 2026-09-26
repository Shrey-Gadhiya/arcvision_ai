# ARC VISION — Model Registry & Perception Architecture

## 1. Supported AI Models & Formats

| Model Task | Primary Model | Supported Formats | Target Precision | Hardware Acceleration |
| :--- | :--- | :--- | :--- | :--- |
| **Object Detection** | YOLOv8 / YOLOv10 / YOLOv11 | `.pt`, `.onnx`, `OpenVINO IR`, `.engine` | FP16 / INT8 | TensorRT, OpenVINO, CUDA |
| **Face Detection** | OpenCV DNN ResNet-10 / UltraFace | Caffe, ONNX | FP32 / FP16 | OpenVINO, CUDA, CPU |
| **Face Recognition (Re-ID)**| InsightFace / ArcFace / MobileFaceNet | `.onnx` | FP16 | TensorRT, ONNX Runtime |
| **Vehicle / Plate OCR** | EasyOCR / CRNN / PaddleOCR | PyTorch, ONNX | FP16 / FP32 | CUDA, CPU |
| **Pose & Actions** | YOLOv8-Pose / MediaPipe | `.onnx`, `.pt` | FP16 | CUDA, OpenVINO |
| **Night Enhancement** | Adaptive CLAHE + Retinex | Classical CV / Deep | FP32 | OpenCV OpenCL / CUDA |

---

## 2. Registering a New Model
1. Place weight artifacts in `backend/data/models/`.
2. Register the model metadata in the AI Model Registry UI or via `POST /api/v1/models`.
3. Assign the model to the target camera profile.
