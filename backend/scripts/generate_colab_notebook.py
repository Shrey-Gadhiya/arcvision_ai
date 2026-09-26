import json
from pathlib import Path

notebook_path = Path("notebooks/ARC_VISION_Colab_T4_Deployment.ipynb")
notebook_path.parent.mkdir(parents=True, exist_ok=True)

cells = [
    # 0. Title & Markdown Header
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🛰️ ARC VISION — Google Colab T4 GPU Deployment & Benchmark Notebook\n",
            "\n",
            "**Problem Statement**: SIH26187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure  \n",
            "**Target Hardware**: NVIDIA Tesla T4 (16GB VRAM) / Any CUDA GPU on Google Colab  \n",
            "**Perception Stack**: Real Ultralytics YOLO26 Multi-Tier Detection, Tactical Pose, OpenCV Biometrics, Neural Plate OCR, and MobileNetV3 Appearance Re-ID.  \n",
            "\n",
            "---\n",
            "\n",
            "### 📋 Notebook Pipeline\n",
            "1. **Environment Discovery & GPU Diagnostics** (`nvidia-smi`, CUDA, PyTorch)\n",
            "2. **Official Repository Clone** (`https://github.com/VG31OP/byrehasira-arcvision.git`)\n",
            "3. **System & Linux Dependencies** (`ffmpeg`, `libgl1`, `libglib2.0-0`, etc.)\n",
            "4. **Backend Python Installation** (`backend/requirements.txt`)\n",
            "5. **Frontend Node.js Build** (`npm install && npm run build`)\n",
            "6. **Real YOLO26 GPU Acquisition & Tensor Verification** (`yolo26m.pt`, `cuda:0`)\n",
            "7. **High-Precision GPU Benchmarking** (with `torch.cuda.synchronize()`)\n",
            "8. **CPU vs GPU Performance Analysis**\n",
            "9. **Database Initialization & RBAC User Seeding**\n",
            "10. **FastAPI Backend & React Frontend Startup**\n",
            "11. **Cloudflare Tunnel Provisioning** (Public URL via `trycloudflare.com`)\n",
            "12. **End-to-End Surveillance Pipeline Execution**\n",
            "13. **Live Process Monitoring & Log Inspector**"
        ]
    },

    # 1. Environment Discovery
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. 🔍 Environment & Hardware Discovery\n",
            "Inspect the Colab runtime environment, memory, disk, and NVIDIA GPU availability."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "import sys\n",
            "import platform\n",
            "import psutil\n",
            "import shutil\n",
            "\n",
            "print('=' * 70)\n",
            "print('  ARC VISION — RUNTIME ENVIRONMENT AUDIT')\n",
            "print('=' * 70)\n",
            "print(f'Python Version      : {platform.python_version()} ({sys.executable})')\n",
            "print(f'Operating System    : {platform.system()} {platform.release()} ({platform.machine()})')\n",
            "print(f'Working Directory   : {os.getcwd()}')\n",
            "print(f'CPU Cores Available : {os.cpu_count()}')\n",
            "ram_gb = psutil.virtual_memory().total / (1024 ** 3)\n",
            "disk_gb = shutil.disk_usage('.').free / (1024 ** 3)\n",
            "print(f'System RAM          : {ram_gb:.2f} GB')\n",
            "print(f'Free Disk Space     : {disk_gb:.2f} GB')\n",
            "\n",
            "# Run nvidia-smi\n",
            "print('\\n--- NVIDIA GPU Status ---')\n",
            "!nvidia-smi || echo 'WARNING: nvidia-smi failed. Ensure GPU runtime is enabled (Runtime -> Change runtime type -> T4 GPU).'\n"
        ]
    },

    # 2. PyTorch & CUDA Inspection
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. ⚡ PyTorch & CUDA Diagnostics\n",
            "Verify that PyTorch can actively communicate with the NVIDIA CUDA driver and allocate VRAM."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import torch\n",
            "\n",
            "print('=' * 70)\n",
            "print('  PYTORCH & CUDA ACCELERATION DIAGNOSTICS')\n",
            "print('=' * 70)\n",
            "print(f'PyTorch Version     : {torch.__version__}')\n",
            "cuda_available = torch.cuda.is_available()\n",
            "print(f'CUDA Available      : {cuda_available}')\n",
            "\n",
            "if cuda_available:\n",
            "    print(f'CUDA Version        : {torch.version.cuda}')\n",
            "    print(f'cuDNN Version       : {torch.backends.cudnn.version()}')\n",
            "    print(f'GPU Device Count    : {torch.cuda.device_count()}')\n",
            "    for i in range(torch.cuda.device_count()):\n",
            "        props = torch.cuda.get_device_properties(i)\n",
            "        vram_gb = props.total_memory / (1024 ** 3)\n",
            "        print(f'  [GPU {i}] {props.name} | Total VRAM: {vram_gb:.2f} GB | SMs: {props.multi_processor_count}')\n",
            "    # Test memory allocation\n",
            "    t = torch.zeros((1000, 1000), device='cuda:0')\n",
            "    print('  -> CUDA tensor allocation test: SUCCESSFUL')\n",
            "    del t\n",
            "    torch.cuda.empty_cache()\n",
            "else:\n",
            "    print('ERROR: No CUDA GPU detected! ARC VISION will run in CPU fallback mode.')\n",
            "    print('To enable GPU in Colab: Go to Menu -> Runtime -> Change runtime type -> Select T4 GPU.')\n"
        ]
    },

    # 3. Clone Repository
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 3. 📦 Clone Official GitHub Repository\n",
            "Clone the verified ARC VISION repository from GitHub into `/content/ARCVISION`."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "from pathlib import Path\n",
            "\n",
            "REPO_URL = \"https://github.com/VG31OP/byrehasira-arcvision.git\"\n",
            "TARGET_DIR = Path(\"/content/ARCVISION\")\n",
            "FORCE_RECLONE = False # Set to True to wipe and re-clone fresh\n",
            "\n",
            "if TARGET_DIR.exists() and FORCE_RECLONE:\n",
            "    print(f'Removing existing directory {TARGET_DIR}...')\n",
            "    !rm -rf {TARGET_DIR}\n",
            "\n",
            "if not TARGET_DIR.exists():\n",
            "    print(f'Cloning {REPO_URL} into {TARGET_DIR}...')\n",
            "    !git clone {REPO_URL} {TARGET_DIR}\n",
            "else:\n",
            "    print(f'Repository already present at {TARGET_DIR}. Pulling latest changes...')\n",
            "    %cd {TARGET_DIR}\n",
            "    !git pull origin main || true\n",
            "\n",
            "%cd {TARGET_DIR}\n",
            "\n",
            "print('\\n--- Git Repository State ---')\n",
            "!git branch --show-current\n",
            "!git rev-parse HEAD\n",
            "!git status --short\n"
        ]
    },

    # 4. System Dependencies
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 4. 🛠️ Install Linux System Dependencies\n",
            "Install FFmpeg (for video decoding/encoding), OpenCV runtime libraries (`libgl1`, `libglib2.0-0`), and build tools."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print('Installing system packages for video processing & computer vision...')\n",
            "!apt-get update -qq && apt-get install -y -qq ffmpeg libgl1 libglib2.0-0 build-essential curl wget > /dev/null\n",
            "\n",
            "print('\\n--- Verifying System Tools ---')\n",
            "!ffmpeg -version | head -n 1\n",
            "!git --version\n",
            "!curl --version | head -n 1\n"
        ]
    },

    # 5. Backend Python Dependencies
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 5. 🐍 Install Backend Python Dependencies\n",
            "Install all packages specified in `backend/requirements.txt`."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "%cd /content/ARCVISION/backend\n",
            "print('Installing backend Python dependencies from requirements.txt...')\n",
            "!pip install -q -r requirements.txt\n",
            "\n",
            "# Verify key imports\n",
            "import fastapi\n",
            "import uvicorn\n",
            "import ultralytics\n",
            "import cv2\n",
            "import supervision\n",
            "\n",
            "print(f'FastAPI Version     : {fastapi.__version__}')\n",
            "print(f'Uvicorn Version     : {uvicorn.__version__}')\n",
            "print(f'Ultralytics Version : {ultralytics.__version__}')\n",
            "print(f'OpenCV Version      : {cv2.__version__}')\n",
            "print(f'Supervision Version : {supervision.__version__}')\n"
        ]
    },

    # 6. Frontend Dependencies & Build
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 6. ⚛️ Install Frontend Dependencies & Build Production Bundle\n",
            "Compile the React + TypeScript frontend application using Vite."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "%cd /content/ARCVISION/frontend\n",
            "print('Checking Node.js & npm...')\n",
            "!node --version\n",
            "!npm --version\n",
            "\n",
            "print('\\nInstalling frontend npm dependencies...')\n",
            "!npm install --quiet\n",
            "\n",
            "print('\\nBuilding production bundle (Vite + TypeScript)...')\n",
            "!npm run build\n",
            "\n",
            "dist_html = Path(\"/content/ARCVISION/frontend/dist/index.html\")\n",
            "if dist_html.exists():\n",
            "    print(f'\\nSUCCESS: Frontend built successfully! Dist size: {dist_html.stat().st_size} bytes.')\n",
            "else:\n",
            "    raise RuntimeError('Frontend build failed. dist/index.html not generated.')\n"
        ]
    },

    # 7. YOLO26 Model Verification on GPU
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 7. 🎯 Acquire & Verify Real YOLO26 Models on GPU\n",
            "Load the real Ultralytics YOLO26 detection family (`yolo26s.pt`, `yolo26m.pt`, `yolo26l.pt`), move them to `cuda:0`, and run inference on test frames."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "%cd /content/ARCVISION/backend\n",
            "import torch\n",
            "import numpy as np\n",
            "from ultralytics import YOLO\n",
            "\n",
            "device = \"cuda:0\" if torch.cuda.is_available() else \"cpu\"\n",
            "print(f'Active Deployment Target Device: {device}')\n",
            "\n",
            "models_to_test = [\"yolo26s.pt\", \"yolo26m.pt\", \"yolo26l.pt\"]\n",
            "verified_models = {}\n",
            "\n",
            "for m_name in models_to_test:\n",
            "    print(f'\\n--- Testing {m_name} on {device} ---')\n",
            "    try:\n",
            "        model = YOLO(m_name)\n",
            "        if device.startswith('cuda'):\n",
            "            model.to(device)\n",
            "            \n",
            "        # Test frame (640x640 synthetic RGB)\n",
            "        test_frame = np.zeros((640, 640, 3), dtype=np.uint8)\n",
            "        results = model(test_frame, device=device, verbose=False)\n",
            "        \n",
            "        param_count = sum(p.numel() for p in model.model.parameters())\n",
            "        layer_count = len(list(model.model.modules()))\n",
            "        \n",
            "        verified_models[m_name] = {\n",
            "            \"task\": model.task,\n",
            "            \"params\": param_count,\n",
            "            \"layers\": layer_count,\n",
            "            \"device\": device\n",
            "        }\n",
            "        print(f'SUCCESS: {m_name} loaded and executed!')\n",
            "        print(f'  Task: {model.task} | Parameters: {param_count:,} | Modules: {layer_count}')\n",
            "    except Exception as e:\n",
            "        print(f'FAILED to load/run {m_name}: {e}')\n",
            "\n",
            "# Run the official repository audit script\n",
            "print('\\n--- Updating Provenance Manifest ---')\n",
            "!python scripts/audit_yolo26_and_hashes.py\n"
        ]
    },

    # 8. High-Precision GPU Benchmark Suite
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 8. 📊 High-Precision GPU Benchmarking\n",
            "Measure cold start, warmup, mean latency, P95 latency, throughput (FPS), and GPU VRAM consumption using `torch.cuda.synchronize()`."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import time\n",
            "import statistics\n",
            "import torch\n",
            "import numpy as np\n",
            "from ultralytics import YOLO\n",
            "\n",
            "def benchmark_gpu(model_name: str, iterations: int = 30, warmup: int = 10):\n",
            "    device = \"cuda:0\" if torch.cuda.is_available() else \"cpu\"\n",
            "    model = YOLO(model_name)\n",
            "    if device.startswith('cuda'):\n",
            "        model.to(device)\n",
            "        torch.cuda.empty_cache()\n",
            "        torch.cuda.reset_peak_memory_stats()\n",
            "        \n",
            "    img = np.zeros((640, 640, 3), dtype=np.uint8)\n",
            "    \n",
            "    # 1. Warmup\n",
            "    for _ in range(warmup):\n",
            "        _ = model(img, device=device, verbose=False)\n",
            "        if device.startswith('cuda'):\n",
            "            torch.cuda.synchronize()\n",
            "            \n",
            "    # 2. Measured Inferences\n",
            "    latencies = []\n",
            "    for _ in range(iterations):\n",
            "        if device.startswith('cuda'):\n",
            "            torch.cuda.synchronize()\n",
            "        t0 = time.perf_counter()\n",
            "        _ = model(img, device=device, verbose=False)\n",
            "        if device.startswith('cuda'):\n",
            "            torch.cuda.synchronize()\n",
            "        t1 = time.perf_counter()\n",
            "        latencies.append((t1 - t0) * 1000.0) # ms\n",
            "        \n",
            "    mean_ms = statistics.mean(latencies)\n",
            "    median_ms = statistics.median(latencies)\n",
            "    sorted_lat = sorted(latencies)\n",
            "    p95_ms = sorted_lat[int(len(sorted_lat) * 0.95)]\n",
            "    p99_ms = sorted_lat[int(len(sorted_lat) * 0.99)]\n",
            "    fps = 1000.0 / mean_ms if mean_ms > 0 else 0.0\n",
            "    params = sum(p.numel() for p in model.model.parameters())\n",
            "    \n",
            "    vram_alloc_mb = 0.0\n",
            "    vram_peak_mb = 0.0\n",
            "    if device.startswith('cuda'):\n",
            "        vram_alloc_mb = torch.cuda.memory_allocated(0) / (1024 * 1024)\n",
            "        vram_peak_mb = torch.cuda.max_memory_allocated(0) / (1024 * 1024)\n",
            "        \n",
            "    return {\n",
            "        \"model\": model_name,\n",
            "        \"params_m\": round(params / 1e6, 2),\n",
            "        \"device\": device,\n",
            "        \"mean_ms\": round(mean_ms, 2),\n",
            "        \"median_ms\": round(median_ms, 2),\n",
            "        \"p95_ms\": round(p95_ms, 2),\n",
            "        \"p99_ms\": round(p99_ms, 2),\n",
            "        \"fps\": round(fps, 1),\n",
            "        \"vram_alloc_mb\": round(vram_alloc_mb, 1),\n",
            "        \"vram_peak_mb\": round(vram_peak_mb, 1)\n",
            "    }\n",
            "\n",
            "print('=' * 100)\n",
            "print('  ARC VISION — GPU INFERENCE BENCHMARK')\n",
            "print('=' * 100)\n",
            "\n",
            "bench_models = [\"yolo26s.pt\", \"yolo26m.pt\", \"yolo26l.pt\", \"yolo26x.pt\"]\n",
            "gpu_results = []\n",
            "\n",
            "for m in bench_models:\n",
            "    print(f'Benchmarking {m}...')\n",
            "    res = benchmark_gpu(m, iterations=25, warmup=5)\n",
            "    gpu_results.append(res)\n",
            "\n",
            "print('\\n' + '=' * 105)\n",
            "print(f'{\"MODEL\":<12} | {\"PARAMS\":<8} | {\"DEVICE\":<8} | {\"MEAN (ms)\":<10} | {\"P95 (ms)\":<10} | {\"FPS\":<8} | {\"VRAM ALLOC\":<12} | {\"VRAM PEAK\":<12}')\n",
            "print('-' * 105)\n",
            "for r in gpu_results:\n",
            "    print(f'{r[\"model\"]:<12} | {r[\"params_m\"]:>6.1f}M | {r[\"device\"]:^8} | {r[\"mean_ms\"]:>10.2f} | {r[\"p95_ms\"]:>10.2f} | {r[\"fps\"]:>8.1f} | {r[\"vram_alloc_mb\"]:>9.1f} MB | {r[\"vram_peak_mb\"]:>9.1f} MB')\n",
            "print('=' * 105)\n"
        ]
    },

    # 9. Direct CPU vs GPU Comparison Table
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 9. 📈 Direct CPU vs GPU Performance Comparison\n",
            "Compare the host CPU measurements against the accelerated GPU benchmarks."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Baseline CPU numbers from ARC VISION host benchmark\n",
            "cpu_baseline = {\n",
            "    \"yolo26s.pt\": {\"mean_ms\": 633.8, \"p95_ms\": 809.8, \"fps\": 1.6},\n",
            "    \"yolo26m.pt\": {\"mean_ms\": 1327.9, \"p95_ms\": 1510.4, \"fps\": 0.8},\n",
            "    \"yolo26l.pt\": {\"mean_ms\": 1389.6, \"p95_ms\": 1904.2, \"fps\": 0.7},\n",
            "    \"yolo26x.pt\": {\"mean_ms\": 2532.3, \"p95_ms\": 2585.0, \"fps\": 0.4}\n",
            "}\n",
            "\n",
            "print('=' * 105)\n",
            "print('                      ARC VISION — CPU vs GPU LATENCY & SPEEDUP MATRIX                      ')\n",
            "print('=' * 105)\n",
            "print(f'{\"MODEL\":<12} | {\"CPU MEAN\":<10} | {\"CPU FPS\":<8} | {\"GPU MEAN\":<10} | {\"GPU FPS\":<8} | {\"SPEEDUP\":<10} | {\"LATENCY REDUCTION\":<18}')\n",
            "print('-' * 105)\n",
            "for gr in gpu_results:\n",
            "    m_name = gr[\"model\"]\n",
            "    cpu_data = cpu_baseline.get(m_name, {\"mean_ms\": 0.0, \"fps\": 0.0})\n",
            "    cpu_mean = cpu_data[\"mean_ms\"]\n",
            "    gpu_mean = gr[\"mean_ms\"]\n",
            "    speedup = round(cpu_mean / max(0.001, gpu_mean), 1) if gpu_mean > 0 and cpu_mean > 0 else 1.0\n",
            "    latency_drop_pct = round(((cpu_mean - gpu_mean) / max(0.001, cpu_mean)) * 100.0, 1) if cpu_mean > 0 else 0.0\n",
            "    print(f'{m_name:<12} | {cpu_mean:>8.1f}ms | {cpu_data[\"fps\"]:>6.1f} | {gpu_mean:>8.1f}ms | {gr[\"fps\"]:>6.1f} | {speedup:>8.1f}x | {latency_drop_pct:>16.1f}%')\n",
            "print('=' * 105)\n"
        ]
    },

    # 10. Database Initialization
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 10. 🗄️ Database Initialization & Migration\n",
            "Initialize the SQLite database schema and seed default RBAC accounts (`admin`, `commander`, `operator`)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "%cd /content/ARCVISION/backend\n",
            "import asyncio\n",
            "from app.core.database import init_db, AsyncSessionLocal\n",
            "from app.models.user import User\n",
            "from sqlalchemy import select\n",
            "\n",
            "async def setup_database():\n",
            "    print('Initializing ARC VISION database tables...')\n",
            "    await init_db()\n",
            "    async with AsyncSessionLocal() as session:\n",
            "        result = await session.execute(select(User))\n",
            "        users = result.scalars().all()\n",
            "        print(f'Database initialized successfully! Seeded users count: {len(users)}')\n",
            "        for u in users:\n",
            "            print(f'  - User: {u.username:<12} | Role: {u.role.value:<10} | Email: {u.email}')\n",
            "\n",
            "await setup_database()\n"
        ]
    },

    # 11. Process Management & Background Services
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 11. 🚀 Process Management & Service Launcher\n",
            "Helper functions to start, stop, monitor, and view logs for the FastAPI backend and React frontend."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import subprocess\n",
            "import time\n",
            "import os\n",
            "import signal\n",
            "import requests\n",
            "\n",
            "BACKEND_LOG = \"/tmp/arcvision_backend.log\"\n",
            "FRONTEND_LOG = \"/tmp/arcvision_frontend.log\"\n",
            "TUNNEL_LOG = \"/tmp/arcvision_tunnel.log\"\n",
            "\n",
            "backend_proc = None\n",
            "frontend_proc = None\n",
            "tunnel_proc = None\n",
            "\n",
            "def start_backend():\n",
            "    global backend_proc\n",
            "    if backend_proc and backend_proc.poll() is None:\n",
            "        print('Backend process already running (PID:', backend_proc.pid, ')')\n",
            "        return\n",
            "    print('Starting FastAPI backend server on 0.0.0.0:8000...')\n",
            "    env = os.environ.copy()\n",
            "    env[\"PYTHONPATH\"] = \"/content/ARCVISION/backend\"\n",
            "    env[\"ARCVISION_DEVICE\"] = \"cuda:0\" if torch.cuda.is_available() else \"cpu\"\n",
            "    backend_proc = subprocess.Popen(\n",
            "        [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"],\n",
            "        cwd=\"/content/ARCVISION/backend\",\n",
            "        env=env,\n",
            "        stdout=open(BACKEND_LOG, \"w\"),\n",
            "        stderr=subprocess.STDOUT\n",
            "    )\n",
            "    print(f'Backend launched with PID: {backend_proc.pid}')\n",
            "\n",
            "def start_frontend():\n",
            "    global frontend_proc\n",
            "    if frontend_proc and frontend_proc.poll() is None:\n",
            "        print('Frontend process already running (PID:', frontend_proc.pid, ')')\n",
            "        return\n",
            "    print('Starting React / Vite frontend server on 0.0.0.0:5173...')\n",
            "    frontend_proc = subprocess.Popen(\n",
            "        [\"npm\", \"run\", \"preview\", \"--\", \"--host\", \"0.0.0.0\", \"--port\", \"5173\"],\n",
            "        cwd=\"/content/ARCVISION/frontend\",\n",
            "        stdout=open(FRONTEND_LOG, \"w\"),\n",
            "        stderr=subprocess.STDOUT\n",
            "    )\n",
            "    print(f'Frontend launched with PID: {frontend_proc.pid}')\n",
            "\n",
            "def show_backend_logs(lines: int = 30):\n",
            "    if os.path.exists(BACKEND_LOG):\n",
            "        print('=' * 80)\n",
            "        print(f'  BACKEND LOGS (last {lines} lines)  ')\n",
            "        print('=' * 80)\n",
            "        !tail -n {lines} {BACKEND_LOG}\n",
            "    else:\n",
            "        print('No backend log found.')\n",
            "\n",
            "def show_frontend_logs(lines: int = 30):\n",
            "    if os.path.exists(FRONTEND_LOG):\n",
            "        print('=' * 80)\n",
            "        print(f'  FRONTEND LOGS (last {lines} lines)  ')\n",
            "        print('=' * 80)\n",
            "        !tail -n {lines} {FRONTEND_LOG}\n",
            "    else:\n",
            "        print('No frontend log found.')\n",
            "\n",
            "def stop_all():\n",
            "    global backend_proc, frontend_proc, tunnel_proc\n",
            "    for p, name in [(backend_proc, 'Backend'), (frontend_proc, 'Frontend'), (tunnel_proc, 'Tunnel')]:\n",
            "        if p and p.poll() is None:\n",
            "            print(f'Stopping {name} (PID: {p.pid})...')\n",
            "            p.terminate()\n",
            "            p.wait(timeout=5)\n",
            "    !pkill -f uvicorn || true\n",
            "    !pkill -f vite || true\n",
            "    !pkill -f cloudflared || true\n",
            "    print('All ARC VISION background processes stopped.')\n",
            "\n",
            "# Start services\n",
            "start_backend()\n",
            "start_frontend()\n"
        ]
    },

    # 12. Health Check Gate
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 12. 🩺 Backend Readiness & Health Check Gate\n",
            "Poll the backend `/api/v1/health` and `/api/v1/models` endpoints until the tactical perception core is fully initialized."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import time\n",
            "import requests\n",
            "\n",
            "HEALTH_URL = \"http://127.0.0.1:8000/api/v1/health\"\n",
            "MODELS_URL = \"http://127.0.0.1:8000/api/v1/models\"\n",
            "\n",
            "print('Waiting for FastAPI backend readiness...')\n",
            "ready = False\n",
            "for attempt in range(1, 25):\n",
            "    try:\n",
            "        r = requests.get(HEALTH_URL, timeout=2)\n",
            "        if r.status_code == 200:\n",
            "            ready = True\n",
            "            print(f'Backend READY on attempt {attempt}! Status: {r.json()}')\n",
            "            break\n",
            "    except Exception:\n",
            "        pass\n",
            "    time.sleep(1.5)\n",
            "\n",
            "if not ready:\n",
            "    show_backend_logs(40)\n",
            "    raise RuntimeError('Backend failed to start within timeout. Check logs above.')\n",
            "\n",
            "# Query live model endpoints\n",
            "try:\n",
            "    models_res = requests.get(MODELS_URL, timeout=3)\n",
            "    print('\\n--- Live Model Registry API ---')\n",
            "    print(models_res.json())\n",
            "except Exception as e:\n",
            "    print(f'Note: Models endpoint check: {e}')\n"
        ]
    },

    # 13. Cloudflare Tunnel
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 13. 🌐 Cloudflare Tunnel Setup (Public Internet URL)\n",
            "Download official `cloudflared` binary and create a zero-configuration public tunnel to expose ARC VISION publicly."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import subprocess\n",
            "import re\n",
            "import time\n",
            "from pathlib import Path\n",
            "\n",
            "# 1. Download cloudflared if not installed\n",
            "if not shutil.which(\"cloudflared\"):\n",
            "    print('Downloading official cloudflared binary for Linux x86_64...')\n",
            "    !wget -q -nc https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb\n",
            "    !dpkg -i cloudflared-linux-amd64.deb > /dev/null\n",
            "\n",
            "print('cloudflared version:', subprocess.getoutput('cloudflared --version'))\n",
            "\n",
            "# 2. Launch Tunnel for frontend (5173) or backend\n",
            "TUNNEL_LOG = \"/tmp/arcvision_tunnel.log\"\n",
            "!pkill -f cloudflared || true\n",
            "\n",
            "print('Starting Cloudflare Tunnel to port 5173 (React UI)...')\n",
            "tunnel_proc = subprocess.Popen(\n",
            "    [\"cloudflared\", \"tunnel\", \"--url\", \"http://localhost:5173\"],\n",
            "    stdout=open(TUNNEL_LOG, \"w\"),\n",
            "    stderr=subprocess.STDOUT\n",
            ")\n",
            "\n",
            "# Extract public URL\n",
            "public_url = None\n",
            "for _ in range(20):\n",
            "    time.sleep(1.0)\n",
            "    if Path(TUNNEL_LOG).exists():\n",
            "        content = Path(TUNNEL_LOG).read_text()\n",
            "        matches = re.findall(r'https://[a-zA-Z0-9-]+\\.trycloudflare\\.com', content)\n",
            "        if matches:\n",
            "            public_url = matches[0]\n",
            "            break\n",
            "\n",
            "if public_url:\n",
            "    print('\\n' + '=' * 80)\n",
            "    print(f'🎉 PUBLIC ARC VISION INTERFACE : {public_url}')\n",
            "    print('=' * 80)\n",
            "else:\n",
            "    print('Warning: Cloudflare URL not captured yet. Checking log:')\n",
            "    !cat {TUNNEL_LOG} | tail -n 20\n"
        ]
    },

    # 14. Dashboard Display
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 14. 🖥️ Mission Command Dashboard\n",
            "Summary dashboard containing active URLs, credentials, Git provenance, and device status."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import subprocess\n",
            "import torch\n",
            "\n",
            "git_commit = subprocess.getoutput(\"git rev-parse --short HEAD\")\n",
            "gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"\n",
            "\n",
            "print(\"=\" * 85)\n",
            "print(\"             ARC VISION — BORDER SURVEILLANCE MISSION CONTROL             \")\n",
            "print(\"=\" * 85)\n",
            "print(f\"Git Commit Hash      : {git_commit}\")\n",
            "print(f\"Active GPU Hardware  : {gpu_name}\")\n",
            "print(f\"PyTorch & CUDA       : PyTorch {torch.__version__} | CUDA {torch.version.cuda if torch.cuda.is_available() else 'N/A'}\")\n",
            "print(f\"Primary AI Detector  : YOLO26m (Active / GPU Accelerated)\")\n",
            "print(f\"Fast Path Detector   : YOLO26s (Active / GPU Accelerated)\")\n",
            "print(f\"Fallback Perimeter   : YOLOv8n (Standby)\")\n",
            "print(\"-\" * 85)\n",
            "print(f\"Local Backend URL    : http://127.0.0.1:8000\")\n",
            "print(f\"Local Frontend URL   : http://127.0.0.1:5173\")\n",
            "print(f\"Backend API Docs     : http://127.0.0.1:8000/docs\")\n",
            "print(f\"Public Cloudflare UI : {public_url or 'See Tunnel Cell Above'}\")\n",
            "print(\"-\" * 85)\n",
            "print(\"Default RBAC Login Credentials:\")\n",
            "print(\"  • Admin Role       : admin / admin123 (Full system control & config)\")\n",
            "print(\"  • Commander Role   : commander / command123 (Incident & dispatch approval)\")\n",
            "print(\"  • Operator Role    : operator / operator123 (Tactical map & live feeds)\")\n",
            "print(\"=\" * 85)\n"
        ]
    },

    # 15. E2E Surveillance Pipeline Verification
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 15. 🧪 Run End-to-End Surveillance Pipeline Verification\n",
            "Execute the complete end-to-end integration test validating video decoding, object detection, tracking, spatial rules, face biometrics, CRNN plate OCR, and cryptographically verified evidence packaging."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "%cd /content/ARCVISION/backend\n",
            "print('Executing Full Surveillance E2E Pipeline Verification...')\n",
            "!python tests/verify_e2e_pipeline.py\n"
        ]
    },

    # 16. Live GPU & Service Monitor
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 16. 📡 Live Monitoring & Process Inspector\n",
            "Run this cell to check live GPU utilization, backend logs, or memory consumption while the platform is processing video feeds."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Print live GPU status\n",
            "!nvidia-smi\n",
            "\n",
            "# Show recent backend logs\n",
            "show_backend_logs(20)\n"
        ]
    },

    # 17. Graceful Shutdown
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 17. 🛑 Teardown / Shutdown Services\n",
            "Stop all running background services (FastAPI, React preview, Cloudflare Tunnel)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "stop_all()\n"
        ]
    }
]

notebook_json = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "name": "ARC_VISION_Colab_T4_Deployment.ipynb",
            "provenance": []
        },
        "gpuClass": "standard",
        "language_info": {
            "name": "python",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(notebook_json, f, indent=2)

print(f"Generated {notebook_path} with {len(cells)} cells.")
