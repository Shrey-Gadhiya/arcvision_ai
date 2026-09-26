# ARC VISION — Troubleshooting & Diagnostic Guide

## 1. Common Diagnostic Scenarios

### Camera Stream Shows OFFLINE or DEGRADED
- **Symptom**: Camera tile shows black screen or status badge is `OFFLINE`.
- **Diagnosis**:
  1. Test network connectivity: `ping <camera_ip>`.
  2. Verify RTSP stream in VLC or with ffprobe: `ffprobe -i "rtsp://user:pass@ip:554/stream"`.
  3. Check backend stream worker logs in terminal.
- **Resolution**: Verify credentials, adjust RTSP transport from UDP to TCP in camera settings, or restart camera stream from the UI.

### CUDA / GPU Acceleration Not Utilized
- **Symptom**: Backend runs on CPU with ~2–5 FPS instead of 30+ FPS.
- **Diagnosis**:
  1. Run `nvidia-smi` to verify GPU presence and driver status.
  2. Check PyTorch CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`.
- **Resolution**: Install CUDA-enabled PyTorch (`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`) or configure TensorRT / OpenVINO acceleration.

### Database Lock Issues (SQLite)
- **Symptom**: `database is locked` error in concurrent heavy multi-camera environments.
- **Resolution**: The system enables SQLite WAL (`Write-Ahead Logging`) mode automatically with a 30s busy timeout. For multi-node or high-scale deployments, switch `DATABASE_URL` in `.env` to PostgreSQL:
  ```env
  DATABASE_URL=postgresql+asyncpg://postgres:pass@localhost:5432/arc_vision
  ```
