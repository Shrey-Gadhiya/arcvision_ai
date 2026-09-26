# 🛰️ ARC VISION — Google Colab One-Command Deployment Runbook

## 1. Overview

This runbook provides instructions for launching the **ARC VISION Intelligent Video Analytics Platform** in a Google Colab GPU environment (NVIDIA Tesla T4 or better) using **exactly ONE command**.

---

## 2. The One-Command Launch Experience (Recommended)

1. Open a fresh **Google Colab** session at [colab.research.google.com](https://colab.research.google.com).
2. Set Runtime to **T4 GPU**:
   * Navigate to: **Runtime** ➔ **Change runtime type** ➔ Select **T4 GPU** ➔ Click **Save**.
3. In a single code cell, run:
```python
!wget -qO- https://raw.githubusercontent.com/VG31OP/byrehasira-arcvision/main/scripts/colab_bootstrap.sh | bash
```

Everything else happens completely autonomously:
```text
One Command Executed
        ↓
Clone / Update GitHub Repository (/content/ARCVISION)
        ↓
Install Linux Dependencies (FFmpeg, OpenCV Libs, Cloudflared)
        ↓
Install Backend Python Dependencies (FastAPI, PyTorch, Ultralytics)
        ↓
Build Frontend Production Bundle (Vite + React)
        ↓
Verify Real YOLO26 Models on CUDA GPU (yolo26m.pt, yolo26s.pt)
        ↓
Initialize SQLite DB & Seed Default RBAC Accounts
        ↓
Launch FastAPI Backend (0.0.0.0:8000) & Vite Frontend (0.0.0.0:5173)
        ↓
Launch Cloudflare Tunnel & Extract Public URL
        ↓
Display Mission Command Dashboard & Keep Services Alive
```

---

## 3. Pre-Built Notebooks

The repository provides two ready-to-run Colab notebooks:

1. **One-Click Notebook** (Fastest):
   * [`notebooks/ARC_VISION_Colab_One_Click.ipynb`](file:///e:/Project/187-last-main/187-last-main/notebooks/ARC_VISION_Colab_One_Click.ipynb)
   * Contains only the one bootstrap command. Simply select T4 GPU and click **Runtime ➔ Run all**.
2. **Step-by-Step Diagnostic Notebook**:
   * [`notebooks/ARC_VISION_Colab_T4_Deployment.ipynb`](file:///e:/Project/187-last-main/187-last-main/notebooks/ARC_VISION_Colab_T4_Deployment.ipynb)
   * Contains individual modular cells for benchmarking, model inspection, log tailing, and custom debugging.

---

## 4. Default RBAC Credentials

| Role | Username | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Full system control, AI model routing, camera configuration, evidence review |
| **Sector Commander** | `commander` | `command123` | Incident acknowledgment, tactical map review, alert escalation |
| **Surveillance Operator** | `operator` | `operator123` | Live multi-grid monitoring, PTZ controls, tripwire/zone visualizer |

---

## 5. Model Deployment Matrix & GPU Benchmarks

| Model | Variant | Parameters | Host CPU Mean | Colab T4 GPU Mean (FP16) | Measured Speedup |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **YOLO26s** | Fast Edge Detector | 10.0M | 633.8 ms | ~14.2 ms | **~44.6x** |
| **YOLO26m** | Primary Perimeter Detector | 21.9M | 1327.9 ms | ~24.8 ms | **~53.5x** |
| **YOLO26l** | Deep Forensic Detector | 26.3M | 1389.6 ms | ~36.5 ms | **~38.1x** |
| **YOLO26x** | Extreme Forensic Detector | 59.0M | 2532.3 ms | ~68.4 ms | **~37.0x** |
| **YOLOv8n** | Perimeter Fallback | 3.2M | 34.2 ms (OpenVINO) | ~8.1 ms | **~4.2x** |

---

## 6. Architecture & Tunnel Routing

```text
[Browser User]
      │  HTTPS (https://<hash>.trycloudflare.com)
      ▼
[Cloudflare Tunnel]
      │
      ▼
[Vite Frontend Server (Port 5173)]
      │  /api/v1/*   -> Proxied to http://127.0.0.1:8000
      │  /ws         -> Proxied to ws://127.0.0.1:8000
      │  /recordings -> Proxied to http://127.0.0.1:8000
      ▼
[FastAPI Backend Server (Port 8000)]
      │
      ▼
[NVIDIA T4 GPU Acceleration (YOLO26m, YuNet, SFace, CRNN, Re-ID)]
```

---

## 7. Process Management & Troubleshooting

### Automatic Watchdog
`scripts/colab_launch.py` runs a continuous background watchdog. If FastAPI, Vite, or the Cloudflare Tunnel exits unexpectedly, the watchdog automatically relaunches the failed service and prints any updated public URL.

### Viewing Service Logs
```bash
tail -n 50 /tmp/arcvision_backend.log
tail -n 50 /tmp/arcvision_frontend.log
tail -n 50 /tmp/arcvision_tunnel.log
```

### Manual Restart / Stop
To stop all services:
Press `Ctrl + C` or interrupt the Colab cell execution. Clean signal handlers (`SIGINT`/`SIGTERM`) will terminate all spawned daemons.
