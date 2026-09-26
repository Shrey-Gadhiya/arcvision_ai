# ARC VISION — Deployment & Infrastructure Guide

## Supported Deployment Targets

| Environment | Inference Backend | Target Hardware | Recommended Profile |
| :--- | :--- | :--- | :--- |
| **Local / Edge Workstation** | OpenVINO / CPU / DirectML | Intel/AMD CPU or integrated iGPU | `APP_ENV=development`, FPS=15 |
| **GPU Workstation** | TensorRT / ONNX CUDA / PyTorch CUDA | NVIDIA RTX 3080/4090 (8GB–24GB VRAM) | `INFERENCE_DEVICE=cuda:0`, FP16 |
| **Multi-GPU Command Server** | TensorRT Multi-Worker Grid | 2x-8x NVIDIA A100/H100 / L40S | GPU 0 (Detection), GPU 1 (OCR/Face) |
| **Offline Border Outpost (BOP)**| Local SQLite / Edge Storage | Ruggedized Industrial IPC (Jetson / x86) | Offline sync, Local Ring Buffer |

---

## 1. Quickstart (Bare-Metal / Local Development)

### Prerequisites
- Python 3.10 to 3.14
- Node.js 18+ & npm
- FFmpeg (optional, recommended for RTSP transcoding)

### Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python run_backend.py
```
The FastAPI backend will start at `http://localhost:8000`.
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The React tactical interface will start at `http://localhost:5173`.

---

## 2. Production Docker Deployment

### Docker Compose Architecture
```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql+asyncpg://postgres:secure_pass@db:5432/arc_vision
      - SECRET_KEY=your-production-high-entropy-secret-key
    volumes:
      - arc_data:/app/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  arc_data:
```

---

## 3. High Availability & Resilience Policies
1. **Worker Restarts**: When an RTSP stream connection drops, `StreamManager` applies exponential backoff reconnection (1s, 2s, 4s, 8s up to max 30s) without halting remaining active workers.
2. **Backpressure & Frame Dropping**: If inference latency spikes, intermediate video frames are safely skipped to preserve real-time low-latency synchronization.
3. **Tamper-Free Storage**: Evidence captures and video clips are stored with immediate SHA-256 computation.
