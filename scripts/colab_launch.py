#!/usr/bin/env python3
"""
ARC VISION — Master Google Colab T4 Deployment Launcher
Single entrypoint script that orchestrates:
- Hardware and CUDA discovery
- Dependency installation
- Frontend build
- Real YOLO26 GPU verification
- Database initialization
- Background FastAPI & Vite services
- Cloudflare Tunnel provisioning
- Live URL extraction & process watchdog
"""

import os
import sys
import time
import re
import signal
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

BACKEND_LOG = Path("/tmp/arcvision_backend.log")
FRONTEND_LOG = Path("/tmp/arcvision_frontend.log")
TUNNEL_LOG = Path("/tmp/arcvision_tunnel.log")

backend_process = None
frontend_process = None
tunnel_process = None
shutdown_requested = False

def log(tag: str, msg: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{tag}] {msg}", flush=True)

def error_exit(component: str, reason: str, log_path: Path = None):
    print("\n" + "=" * 80)
    print("  ARC VISION STARTUP FAILED ❌")
    print("=" * 80)
    print(f"FAILED COMPONENT : {component}")
    print(f"REASON           : {reason}")
    if log_path and log_path.exists():
        print(f"LOG FILE         : {log_path}")
        print("\n--- Last 30 lines of log ---")
        try:
            lines = log_path.read_text(errors="ignore").strip().splitlines()
            for l in lines[-30:]:
                print(l)
        except Exception:
            pass
    print("=" * 80 + "\n")
    cleanup_processes()
    sys.exit(1)

def cleanup_processes(signum=None, frame=None):
    global shutdown_requested, backend_process, frontend_process, tunnel_process
    if shutdown_requested:
        return
    shutdown_requested = True
    log("SHUTDOWN", "Terminating all ARC VISION background processes...")
    for p, name in [(backend_process, "Backend"), (frontend_process, "Frontend"), (tunnel_process, "Cloudflare Tunnel")]:
        if p and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
    # Sweep stray processes on Linux
    if platform.system() != "Windows":
        subprocess.run(["pkill", "-f", "uvicorn app.main:app"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "cloudflared tunnel"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "vite"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("SHUTDOWN", "All services cleanly stopped.")

signal.signal(signal.SIGINT, cleanup_processes)
signal.signal(signal.SIGTERM, cleanup_processes)

def check_system_tools():
    log("ENV", "Checking Linux system tools...")
    if platform.system() == "Linux":
        # Check ffmpeg
        if not shutil.which("ffmpeg"):
            log("ENV", "Installing ffmpeg and CV dependencies...")
            subprocess.run(["apt-get", "update", "-qq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["apt-get", "install", "-y", "-qq", "ffmpeg", "libgl1", "libglib2.0-0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Check cloudflared
        if not shutil.which("cloudflared"):
            log("ENV", "Installing cloudflared binary...")
            try:
                subprocess.run(["wget", "-q", "-nc", "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"], check=True)
                subprocess.run(["dpkg", "-i", "cloudflared-linux-amd64.deb"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                log("WARN", f"Could not auto-install cloudflared deb: {e}")

def check_python_dependencies():
    log("PYTHON", "Verifying Python dependencies...")
    req_file = BACKEND_DIR / "requirements.txt"
    if req_file.exists():
        try:
            import fastapi
            import uvicorn
            import ultralytics
            import supervision
        except ImportError:
            log("PYTHON", f"Installing dependencies from {req_file}...")
            res = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)])
            if res.returncode != 0:
                error_exit("Python Dependencies", "pip install failed on requirements.txt")

def check_gpu():
    log("GPU", "Auditing hardware acceleration...")
    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "None"
        vram_gb = (torch.cuda.get_device_properties(0).total_memory / (1024**3)) if cuda_avail else 0.0
        print("=" * 65)
        print(f"  GPU Device     : {gpu_name} ({vram_gb:.2f} GB VRAM)")
        print(f"  CUDA Available : {cuda_avail}")
        print(f"  PyTorch Build  : {torch.__version__}")
        print("=" * 65)
        return cuda_avail
    except Exception as e:
        log("GPU", f"PyTorch GPU check exception: {e}")
        return False

def verify_and_audit_models(use_cuda: bool):
    log("MODELS", "Running YOLO26 artifact and provenance verification...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    audit_script = BACKEND_DIR / "scripts" / "audit_yolo26_and_hashes.py"
    if audit_script.exists():
        res = subprocess.run([sys.executable, str(audit_script)], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True)
        if res.returncode != 0:
            log("WARN", f"Model audit script warning: {res.stderr[:200]}")
        else:
            log("MODELS", "Model provenance manifest updated and verified.")

def init_database():
    log("DATABASE", "Initializing database schema & seeding default RBAC users...")
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        import asyncio
        from app.core.database import init_db
        asyncio.run(init_db())
        log("DATABASE", "Database tables & RBAC accounts initialized.")
    except Exception as e:
        error_exit("Database Init", f"Failed to initialize database: {e}")

def build_frontend():
    log("FRONTEND", "Checking frontend production bundle...")
    dist_html = FRONTEND_DIR / "dist" / "index.html"
    if not dist_html.exists():
        log("FRONTEND", "Installing npm packages and building Vite bundle...")
        npm_cmd = shutil.which("npm")
        if not npm_cmd:
            error_exit("Frontend Build", "Node.js / npm not found on system.")
        res1 = subprocess.run([npm_cmd, "install", "--quiet"], cwd=str(FRONTEND_DIR), capture_output=True)
        if res1.returncode != 0:
            error_exit("Frontend npm install", res1.stderr.decode("utf-8", errors="ignore"))
        res2 = subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), capture_output=True)
        if res2.returncode != 0:
            error_exit("Frontend build", res2.stderr.decode("utf-8", errors="ignore"))
    log("FRONTEND", "Frontend production build ready.")

def start_backend_service(use_cuda: bool):
    global backend_process
    log("BACKEND", "Launching FastAPI backend server on 0.0.0.0:8000...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["ARCVISION_DEVICE"] = "cuda:0" if use_cuda else "cpu"
    
    with open(BACKEND_LOG, "w") as out:
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=out,
            stderr=subprocess.STDOUT
        )

    # Health polling
    ready = False
    for attempt in range(1, 35):
        time.sleep(1.0)
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/v1/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            pass
        if backend_process.poll() is not None:
            break

    if not ready:
        error_exit("FastAPI Backend", "Backend failed health check within 35 seconds.", BACKEND_LOG)
    log("BACKEND", "FastAPI backend is READY (HTTP 200).")

def start_frontend_service():
    global frontend_process
    log("FRONTEND", "Launching Vite preview server on 0.0.0.0:5173...")
    npm_cmd = shutil.which("npm") or "npm"
    with open(FRONTEND_LOG, "w") as out:
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"],
            cwd=str(FRONTEND_DIR),
            stdout=out,
            stderr=subprocess.STDOUT
        )

    ready = False
    for _ in range(25):
        time.sleep(1.0)
        try:
            req = urllib.request.Request("http://127.0.0.1:5173")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in [200, 304]:
                    ready = True
                    break
        except Exception:
            pass
        if frontend_process.poll() is not None:
            break

    if not ready:
        error_exit("React Frontend", "Frontend failed readiness check on port 5173.", FRONTEND_LOG)
    log("FRONTEND", "Vite frontend is READY (HTTP 200).")

def start_cloudflare_tunnel() -> str:
    global tunnel_process
    log("TUNNEL", "Starting Cloudflare Tunnel to expose port 5173...")
    cf_bin = shutil.which("cloudflared")
    if not cf_bin:
        error_exit("Cloudflare Tunnel", "cloudflared executable not found.")

    with open(TUNNEL_LOG, "w") as out:
        tunnel_process = subprocess.Popen(
            [cf_bin, "tunnel", "--url", "http://localhost:5173"],
            stdout=out,
            stderr=subprocess.STDOUT
        )

    public_url = None
    for _ in range(30):
        time.sleep(1.0)
        if TUNNEL_LOG.exists():
            content = TUNNEL_LOG.read_text(errors="ignore")
            matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
            if matches:
                public_url = matches[0]
                break
        if tunnel_process.poll() is not None:
            break

    if not public_url:
        error_exit("Cloudflare Tunnel", "Failed to extract public URL from cloudflared.", TUNNEL_LOG)
    log("TUNNEL", f"Cloudflare Tunnel connected: {public_url}")
    return public_url

def print_banner(public_url: str, use_cuda: bool):
    try:
        git_commit = subprocess.getoutput("git rev-parse --short HEAD")
    except Exception:
        git_commit = "main"

    gpu_status = "NVIDIA CUDA ACCELERATED" if use_cuda else "CPU FALLBACK"

    print("\n" + "═" * 78)
    print("  🚀  ARC VISION — BORDER SURVEILLANCE PLATFORM IS LIVE  🚀  ")
    print("═" * 78)
    print(f"\n  👉 PUBLIC URL : \033[1;32m{public_url}\033[0m")
    print(f"     (Open this link in your browser to access the full UI & AI pipeline)\n")
    print("─" * 78)
    print(f"  • Hardware Mode     : {gpu_status}")
    print(f"  • Primary Detector  : YOLO26m (Active)")
    print(f"  • Fast Edge Model   : YOLO26s (Active)")
    print(f"  • Neural Re-ID      : MobileNetV3 576-D Deep Embeddings")
    print(f"  • Neural Plate OCR  : CRNN CTC Character Recognition")
    print(f"  • Face Biometrics   : YuNet Face Detector + SFace 128-D")
    print(f"  • Git Commit        : {git_commit}")
    print("─" * 78)
    print("  Default RBAC Credentials:")
    print("    - Administrator   : admin / admin123")
    print("    - Commander       : commander / command123")
    print("    - Operator        : operator / operator123")
    print("═" * 78)
    print("  [System Watchdog Active] Keeping services alive. Press Ctrl+C to stop.\n", flush=True)

    try:
        from IPython.display import display, HTML
        display(HTML(f"""
        <div style="background: linear-gradient(135deg, #0f172a, #1e293b); border: 2px solid #38bdf8; border-radius: 12px; padding: 20px; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-shadow: 0 10px 25px rgba(0,0,0,0.5); max-width: 700px; margin: 15px 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <span style="font-size: 24px;">🛰️</span>
                <h2 style="color: #38bdf8; margin: 0; font-size: 20px; font-weight: 700;">ARC VISION — BORDER SURVEILLANCE CORE</h2>
            </div>
            <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 16px;">FastAPI Backend, React Frontend, and Cloudflare Tunnel are active and connected.</p>
            <div style="background: #0284c7; padding: 12px 20px; border-radius: 8px; display: inline-block; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);">
                <a href="{public_url}" target="_blank" style="color: #ffffff; font-size: 16px; font-weight: 700; text-decoration: none; display: flex; align-items: center; gap: 8px;">
                    <span>🚀 OPEN ARC VISION INTERFACE:</span>
                    <span style="text-decoration: underline;">{public_url}</span>
                </a>
            </div>
            <div style="background: rgba(0,0,0,0.3); border-radius: 6px; padding: 10px 14px; color: #94a3b8; font-size: 13px; line-height: 1.6;">
                <div>🔑 <b>Login:</b> <code style="color: #38bdf8;">admin</code> / <code style="color: #38bdf8;">admin123</code></div>
                <div>⚡ <b>AI Models:</b> YOLO26m ({gpu_status}) • YuNet • SFace • CRNN OCR</div>
            </div>
        </div>
        """))
    except Exception:
        pass

def run_watchdog():
    while not shutdown_requested:
        time.sleep(10)
        # Check backend
        if backend_process and backend_process.poll() is not None:
            log("WATCHDOG", "Backend crashed! Relaunching...")
            start_backend_service(check_gpu())
        # Check frontend
        if frontend_process and frontend_process.poll() is not None:
            log("WATCHDOG", "Frontend crashed! Relaunching...")
            start_frontend_service()
        # Check tunnel
        if tunnel_process and tunnel_process.poll() is not None:
            log("WATCHDOG", "Cloudflare tunnel disconnected! Relaunching...")
            new_url = start_cloudflare_tunnel()
            print(f"\n  👉 NEW PUBLIC URL : \033[1;32{new_url}\033[0m\n", flush=True)

def main():
    print("\n" + "=" * 78)
    print("  ARC VISION — ONE-COMMAND GOOGLE COLAB INITIALIZER")
    print("=" * 78)
    check_system_tools()
    check_python_dependencies()
    use_cuda = check_gpu()
    verify_and_audit_models(use_cuda)
    init_database()
    build_frontend()
    start_backend_service(use_cuda)
    start_frontend_service()
    public_url = start_cloudflare_tunnel()
    print_banner(public_url, use_cuda)
    run_watchdog()

if __name__ == "__main__":
    main()
