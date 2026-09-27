#!/usr/bin/env bash
# ==============================================================================
# ARC VISION — One-Command Google Colab Bootstrap Script
# Usage in Google Colab:
# !wget -qO- https://raw.githubusercontent.com/VG31OP/byrehasira-arcvision/main/scripts/colab_bootstrap.sh | bash
# ==============================================================================

set -e

REPO_URL="${REPO_URL:-https://github.com/VG31OP/byrehasira-arcvision.git}"
BRANCH="${BRANCH:-main}"

if [ -d "/kaggle/working" ]; then
    REPO_DIR="${REPO_DIR:-/kaggle/working/ARCVISION}"
else
    REPO_DIR="${REPO_DIR:-/content/ARCVISION}"
fi

echo "======================================================================"
echo "  🛰️ ARC VISION — ONE-COMMAND BOOTSTRAPPER"
echo "======================================================================"
echo "Target Repository : $REPO_URL"
echo "Target Branch     : $BRANCH"
echo "Target Directory  : $REPO_DIR"
echo "======================================================================"

# Clean any temporary stale paths
rm -rf /tmp/ARCVISION_REPO /tmp/arcvision_logs 2>/dev/null || true

# 1. Clone or Update Repository
if [ ! -d "$REPO_DIR" ]; then
    echo "[ARC VISION] Cloning repository into $REPO_DIR..."
    git clone --quiet "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
else
    echo "[ARC VISION] Updating existing repository at $REPO_DIR..."
    cd "$REPO_DIR"
    git remote set-url origin "$REPO_URL" 2>/dev/null || true
    git fetch origin "$BRANCH" --quiet
    git reset --hard "origin/$BRANCH" --quiet
fi

COMMIT_HASH=$(git rev-parse --short HEAD)
echo "[ARC VISION] Repository updated to commit: $COMMIT_HASH"

# 2. Ensure cloudflared is installed if in Debian/Ubuntu environment
if ! command -v cloudflared &> /dev/null; then
    echo "[ARC VISION] Installing cloudflared binary for Linux x86_64..."
    wget -q -nc https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -O /tmp/cloudflared.deb || true
    if [ -f /tmp/cloudflared.deb ]; then
        dpkg -i /tmp/cloudflared.deb > /dev/null 2>&1 || true
        rm -f /tmp/cloudflared.deb
    fi
fi

# 3. Check GPU and ensure CUDA-enabled PyTorch is present
if command -v nvidia-smi &> /dev/null; then
    echo "[ARC VISION] NVIDIA GPU hardware detected via nvidia-smi."
    if ! python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" &> /dev/null; then
        echo "[ARC VISION] Installing CUDA-enabled PyTorch build (cu121) for full GPU offloading..."
        pip install --quiet --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu121
    else
        echo "[ARC VISION] PyTorch CUDA acceleration is active."
    fi
else
    echo "──────────────────────────────────────────────────────────────────────"
    echo "⚠️  NOTE: No NVIDIA GPU detected in this Colab session!"
    echo "   To offload 100% of AI compute to GPU and achieve 50x higher FPS:"
    echo "   Go to Colab Menu: Runtime ➔ Change runtime type ➔ Select T4 GPU"
    echo "──────────────────────────────────────────────────────────────────────"
fi

# 3. Launch Master Python Orchestrator
echo "[ARC VISION] Launching ARC VISION Master Deployment Controller..."
python3 scripts/colab_launch.py
