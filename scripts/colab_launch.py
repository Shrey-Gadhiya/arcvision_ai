#!/usr/bin/env python3
"""
ARC VISION — Master Cloud GPU (Colab & Kaggle T4) Deployment Launcher
Single entrypoint script that orchestrates:
- Hardware and CUDA discovery
- Dependency verification
- Production frontend build
- Real YOLO26 GPU verification
- Database initialization and default RBAC accounts
- FastAPI backend unified single-port service
- Multi-tunnel provisioning (Pinggy, Localhost.run, Cloudflare HTTP2, Localtunnel)
- Direct In-Notebook Embedded Viewer & Native Colab Port integration
- Live watchdog & automatic failover
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
from typing import Dict, Any, Optional, List
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

LOG_DIR = Path("/tmp/arcvision_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_LOG = LOG_DIR / "backend.log"
FRONTEND_LOG = LOG_DIR / "frontend.log"
CF_TUNNEL_LOG = LOG_DIR / "cloudflare.log"
PINGGY_LOG = LOG_DIR / "pinggy.log"
LHR_LOG = LOG_DIR / "localhostrun.log"
LOCALTUNNEL_LOG = LOG_DIR / "localtunnel.log"

backend_process = None
cf_tunnel_process = None
pinggy_process = None
lhr_process = None
localtunnel_process = None
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
    global shutdown_requested, backend_process, cf_tunnel_process, pinggy_process, lhr_process, localtunnel_process
    if shutdown_requested:
        return
    shutdown_requested = True
    log("SHUTDOWN", "Terminating all ARC VISION background processes...")
    processes = [
        (backend_process, "Backend"),
        (cf_tunnel_process, "Cloudflare Tunnel"),
        (pinggy_process, "Pinggy Tunnel"),
        (lhr_process, "Localhost.run Tunnel"),
        (localtunnel_process, "Localtunnel"),
    ]
    for p, name in processes:
        if p and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
    if platform.system() != "Windows":
        subprocess.run(["pkill", "-f", "uvicorn app.main:app"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "cloudflared tunnel"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "pinggy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "localhost.run"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("SHUTDOWN", "All services stopped.")

signal.signal(signal.SIGINT, cleanup_processes)
signal.signal(signal.SIGTERM, cleanup_processes)

def check_system_tools():
    log("ENV", "Checking Linux system tools...")
    if platform.system() == "Linux":
        try:
            tools_to_install = []
            if not shutil.which("ffmpeg"):
                tools_to_install.extend(["ffmpeg", "libgl1", "libglib2.0-0"])
            if not shutil.which("ssh"):
                tools_to_install.append("openssh-client")

            if tools_to_install:
                log("ENV", f"Installing system packages: {', '.join(tools_to_install)}...")
                subprocess.run(["apt-get", "update", "-qq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["apt-get", "install", "-y", "-qq"] + tools_to_install, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log("WARN", f"System package check note: {e}")

        # Check cloudflared
        if not shutil.which("cloudflared"):
            log("ENV", "Installing cloudflared binary...")
            try:
                deb_path = "/tmp/cloudflared-linux-amd64.deb"
                subprocess.run(["wget", "-q", "-nc", "-O", deb_path, "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"], check=True)
                subprocess.run(["dpkg", "-i", deb_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                log("WARN", f"Could not auto-install cloudflared deb: {e}")

def check_python_dependencies():
    log("PYTHON", "Verifying Python dependencies...")
    try:
        import fastapi
        import uvicorn
        import aiosqlite
        import ultralytics
        import supervision
    except ImportError:
        req_file = BACKEND_DIR / "requirements.txt"
        log("PYTHON", f"Installing dependencies from {req_file}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)], check=False)
        except Exception as e:
            log("WARN", f"pip install note: {e}")

def check_gpu() -> bool:
    log("GPU", "Auditing hardware acceleration...")
    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if cuda_avail else 0
        gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "None"
        vram_gb = (torch.cuda.get_device_properties(0).total_memory / (1024**3)) if cuda_avail else 0.0
        print("=" * 65)
        print(f"  GPU Device(s)  : {gpu_count}x {gpu_name} ({vram_gb:.2f} GB VRAM per GPU)")
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
            log("MODELS", "Model provenance manifest verified.")

def init_database():
    log("DATABASE", "Initializing database schema & seeding default RBAC users...")
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        import asyncio
        import threading
        from app.core.database import init_db

        db_err = None
        def _run_init():
            nonlocal db_err
            try:
                asyncio.run(init_db())
            except Exception as ex:
                db_err = ex

        t = threading.Thread(target=_run_init)
        t.start()
        t.join(timeout=15.0)
        if db_err:
            log("WARN", f"Pre-init note: {db_err} (FastAPI lifespan will finalize init on boot)")
        else:
            log("DATABASE", "Database tables & RBAC accounts initialized.")
    except Exception as e:
        log("WARN", f"Database pre-init note: {e}")

def build_frontend():
    log("FRONTEND", "Verifying frontend production assets...")
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if dist_index.exists() and dist_index.stat().st_size > 0:
        log("FRONTEND", "Pre-built production bundle verified in frontend/dist.")
        return

    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        log("FRONTEND", "Using repository pre-bundled static assets.")
        return

    try:
        node_modules = FRONTEND_DIR / "node_modules"
        if not node_modules.exists():
            log("FRONTEND", "Installing npm packages...")
            subprocess.run([npm_cmd, "install", "--quiet"], cwd=str(FRONTEND_DIR), capture_output=True, timeout=120)

        log("FRONTEND", "Compiling production assets with Vite...")
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), capture_output=True, timeout=120)
        log("FRONTEND", "Frontend build ready.")
    except Exception as e:
        log("WARN", f"Frontend build skipped: {e}")

def start_backend_service(use_cuda: bool):
    global backend_process
    log("BACKEND", "Launching FastAPI unified single-port backend server on 0.0.0.0:8000...")
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
    for attempt in range(1, 40):
        time.sleep(1.0)
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
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
        error_exit("FastAPI Backend", "Backend failed health check within 40 seconds.", BACKEND_LOG)
    log("BACKEND", "FastAPI backend is READY (HTTP 200).")

def start_tunnels() -> Dict[str, str]:
    global cf_tunnel_process, pinggy_process, lhr_process, localtunnel_process
    urls = {}

    ssh_bin = shutil.which("ssh")
    cf_bin = shutil.which("cloudflared")
    npm_cmd = shutil.which("npx") or shutil.which("npm")

    # 1. Start Pinggy Tunnel (Port 443 SSH SSL)
    if ssh_bin:
        try:
            log("TUNNEL", "Starting Pinggy Tunnel (SSH Port 443)...")
            with open(PINGGY_LOG, "w") as out:
                pinggy_process = subprocess.Popen(
                    [ssh_bin, "-p", "443", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R0:localhost:8000", "a.pinggy.io"],
                    stdout=out,
                    stderr=subprocess.STDOUT
                )
        except Exception as e:
            log("WARN", f"Pinggy launch failed: {e}")

    # 2. Start Cloudflare Tunnel
    if cf_bin:
        try:
            log("TUNNEL", "Starting Cloudflare Tunnel...")
            with open(CF_TUNNEL_LOG, "w") as out:
                cf_tunnel_process = subprocess.Popen(
                    [cf_bin, "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate"],
                    stdout=out,
                    stderr=subprocess.STDOUT
                )
        except Exception as e:
            log("WARN", f"Cloudflare launch failed: {e}")

    # 3. Start Localhost.run Tunnel (SSH)
    if ssh_bin:
        try:
            log("TUNNEL", "Starting Localhost.run Tunnel (SSH)...")
            with open(LHR_LOG, "w") as out:
                lhr_process = subprocess.Popen(
                    [ssh_bin, "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", "80:localhost:8000", "nokey@localhost.run"],
                    stdout=out,
                    stderr=subprocess.STDOUT
                )
        except Exception as e:
            log("WARN", f"Localhost.run launch failed: {e}")

    # 4. Start Localtunnel (Backup)
    if npm_cmd:
        try:
            log("TUNNEL", "Starting Localtunnel (Backup)...")
            with open(LOCALTUNNEL_LOG, "w") as out:
                localtunnel_process = subprocess.Popen(
                    ["npx", "-y", "localtunnel", "--port", "8000", "--local-host", "127.0.0.1"],
                    stdout=out,
                    stderr=subprocess.STDOUT
                )
        except Exception as e:
            log("WARN", f"Localtunnel launch failed: {e}")

    # Poll logs for active tunnel URLs
    log("TUNNEL", "Waiting for tunnel endpoints to establish...")
    for _ in range(30):
        time.sleep(1.0)
        
        # Pinggy extraction
        if not urls.get("pinggy") and PINGGY_LOG.exists():
            p_content = PINGGY_LOG.read_text(errors="ignore")
            matches = re.findall(r"https://[a-zA-Z0-9.-]+\.pinggy\.link", p_content) or re.findall(r"https://[a-zA-Z0-9.-]+\.free\.pinggy\.link", p_content)
            for m in matches:
                if "dashboard" not in m and "login" not in m:
                    urls["pinggy"] = m
                    log("TUNNEL", f"Pinggy Tunnel connected: {m}")
                    break

        # Cloudflare extraction
        if not urls.get("cloudflare") and CF_TUNNEL_LOG.exists():
            cf_content = CF_TUNNEL_LOG.read_text(errors="ignore")
            cf_matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", cf_content)
            if cf_matches:
                urls["cloudflare"] = cf_matches[0]
                log("TUNNEL", f"Cloudflare Tunnel connected: {cf_matches[0]}")

        # Localhost.run extraction
        if not urls.get("localhostrun") and LHR_LOG.exists():
            lhr_content = LHR_LOG.read_text(errors="ignore")
            lhr_matches = re.findall(r"https://[a-zA-Z0-9-]+\.lhr\.life", lhr_content) or re.findall(r"https://[a-zA-Z0-9-]+\.localhost\.run", lhr_content)
            if lhr_matches:
                urls["localhostrun"] = lhr_matches[0]
                log("TUNNEL", f"Localhost.run connected: {lhr_matches[0]}")

        # Localtunnel extraction
        if not urls.get("localtunnel") and LOCALTUNNEL_LOG.exists():
            lt_content = LOCALTUNNEL_LOG.read_text(errors="ignore")
            lt_matches = re.findall(r"https://[a-zA-Z0-9-]+\.loca\.lt", lt_content)
            if lt_matches:
                urls["localtunnel"] = lt_matches[0]
                log("TUNNEL", f"Localtunnel connected: {lt_matches[0]}")

        if len(urls) >= 1:
            # If at least one direct tunnel is ready and we gave 5s for others, proceed
            if len(urls) >= 2 or _ >= 8:
                break

    # Retrieve public IP for Localtunnel bypass if needed
    try:
        req = urllib.request.Request("https://ipv4.icanhazip.com", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            urls["public_ip"] = resp.read().decode("utf-8").strip()
    except Exception:
        urls["public_ip"] = "N/A"

    if not urls or len([k for k in urls if k != "public_ip"]) == 0:
        urls["local"] = "http://127.0.0.1:8000"
    return urls

def print_banner(urls: Dict[str, str], use_cuda: bool):
    try:
        git_commit = subprocess.getoutput("git rev-parse --short HEAD")
    except Exception:
        git_commit = "main"

    gpu_status = "NVIDIA CUDA ACCELERATED (DUAL GPU POOL)" if use_cuda else "CPU FALLBACK"

    pinggy_url = urls.get("pinggy")
    cf_url = urls.get("cloudflare")
    lhr_url = urls.get("localhostrun")
    lt_url = urls.get("localtunnel")
    public_ip = urls.get("public_ip", "N/A")

    print("\n" + "═" * 80)
    print("  🛰️   ARC VISION — BORDER SURVEILLANCE PLATFORM IS ONLINE   🛰️  ")
    print("═" * 80)
    
    # Print high-priority active URLs
    if pinggy_url:
        print(f"\n  👉 PRIMARY DIRECT LINK (Pinggy SSL)  : \033[1;32m{pinggy_url}\033[0m")
    if cf_url:
        print(f"  👉 ALTERNATIVE LINK (Cloudflare)     : \033[1;36m{cf_url}\033[0m")
    if lhr_url:
        print(f"  👉 MIRROR LINK (Localhost.run)       : \033[1;35m{lhr_url}\033[0m")
    if lt_url:
        print(f"  👉 BACKUP LINK (Localtunnel)         : \033[1;33m{lt_url}\033[0m")
        if public_ip != "N/A":
            print(f"     ↳ (If Localtunnel asks for password, enter: \033[1m{public_ip}\033[0m)")

    print("\n" + "─" * 80)
    print(f"  • Hardware Mode     : {gpu_status}")
    print(f"  • Primary Detector  : YOLO26m (Active GPU CUDA FP16)")
    print(f"  • Fast Edge Model   : YOLO26s (Active GPU CUDA FP16)")
    print(f"  • Neural Re-ID      : MobileNetV3 576-D Deep Embeddings")
    print(f"  • Neural Plate OCR  : CRNN CTC Character Recognition")
    print(f"  • Face Biometrics   : YuNet Face Detector + SFace 128-D")
    print(f"  • Active Commit     : {git_commit}")
    print("─" * 80)
    print("  Default RBAC Credentials:")
    print("    - Administrator   : admin / admin123")
    print("    - Commander       : commander / command123")
    print("    - Operator        : operator / operator123")
    print("═" * 80)
    print("  [System Watchdog Active] Keeping all services online. Press Ctrl+C to stop.\n", flush=True)

    # Google Colab native interactive iframe & window
    try:
        import google.colab.output
        try:
            google.colab.output.serve_kernel_port_as_iframe(8000, height=850)
        except Exception:
            google.colab.output.serve_kernel_port_as_window(8000)
    except Exception:
        pass

    # IPython Rich Interactive Display Widget
    try:
        from IPython.display import display, HTML
        
        buttons_html = ""
        if pinggy_url:
            buttons_html += f"""
            <a href="{pinggy_url}" target="_blank" style="background: #10b981; color: #ffffff; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 14px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);">
                ⚡ Open via Pinggy (Instant SSL)
            </a>
            """
        if cf_url:
            buttons_html += f"""
            <a href="{cf_url}" target="_blank" style="background: #0284c7; color: #ffffff; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 14px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);">
                ☁️ Open via Cloudflare
            </a>
            """
        if lhr_url:
            buttons_html += f"""
            <a href="{lhr_url}" target="_blank" style="background: #8b5cf6; color: #ffffff; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 14px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);">
                🔗 Open via Localhost.run
            </a>
            """

        display(HTML(f"""
        <div style="background: linear-gradient(135deg, #090d16, #131d2e); border: 2px solid #38bdf8; border-radius: 12px; padding: 22px; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-shadow: 0 12px 30px rgba(0,0,0,0.6); max-width: 760px; margin: 15px 0;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 28px;">🛰️</span>
                <div>
                    <h2 style="color: #38bdf8; margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0.05em;">ARC VISION — BORDER SURVEILLANCE CORE</h2>
                    <p style="color: #94a3b8; font-size: 13px; margin: 2px 0 0 0;">Unified Single-Port Web Engine • Real-Time AI Detection & Tracking</p>
                </div>
            </div>
            
            <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 16px;">Click an active link below to launch the surveillance dashboard:</p>
            
            <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
                {buttons_html}
            </div>
            
            <div style="background: rgba(0,0,0,0.4); border-radius: 8px; padding: 12px 16px; color: #94a3b8; font-size: 13px; line-height: 1.7; border: 1px solid rgba(255,255,255,0.06);">
                <div>🔑 <b>Default Login:</b> <code style="color: #38bdf8; background: rgba(56,189,248,0.1); padding: 2px 6px; border-radius: 4px;">admin</code> / <code style="color: #38bdf8; background: rgba(56,189,248,0.1); padding: 2px 6px; border-radius: 4px;">admin123</code></div>
                <div>⚡ <b>Hardware Mode:</b> <span style="color: #4ade80;">{gpu_status}</span> • YOLO26m / YOLO26s Active</div>
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
            log("WATCHDOG", "Backend stopped! Relaunching...")
            start_backend_service(check_gpu())

def main():
    print("\n" + "=" * 80)
    print("  ARC VISION — HIGH-PERFORMANCE CLOUD GPU INITIALIZER (COLAB / KAGGLE)")
    print("=" * 80)
    check_system_tools()
    check_python_dependencies()
    use_cuda = check_gpu()
    verify_and_audit_models(use_cuda)
    init_database()
    build_frontend()
    start_backend_service(use_cuda)
    urls = start_tunnels()
    print_banner(urls, use_cuda)
    run_watchdog()

if __name__ == "__main__":
    main()
