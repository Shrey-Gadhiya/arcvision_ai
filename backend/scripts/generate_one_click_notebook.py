import json
from pathlib import Path

notebook_path = Path("notebooks/ARC_VISION_Colab_One_Click.ipynb")
notebook_path.parent.mkdir(parents=True, exist_ok=True)

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🛰️ ARC VISION — ONE-COMMAND GOOGLE COLAB LAUNCHER\n",
            "\n",
            "**Problem Statement**: SIH26187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure  \n",
            "**Target Hardware**: NVIDIA Tesla T4 / Any CUDA GPU on Google Colab  \n",
            "\n",
            "---\n",
            "\n",
            "### ⚡ How To Run\n",
            "1. Set runtime to **T4 GPU** (Menu ➔ **Runtime** ➔ **Change runtime type** ➔ **T4 GPU**).\n",
            "2. Run the single cell below (**Ctrl + F9** or **Runtime** ➔ **Run all**).\n",
            "3. Wait ~90 seconds for automatic cloning, dependency setup, YOLO26 GPU verification, and Cloudflare Tunnel provisioning.\n",
            "4. Click the generated **`https://xxxx.trycloudflare.com`** URL to open the live platform!"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ==============================================================================\n",
            "# 🚀 ARC VISION ONE-COMMAND LAUNCHER\n",
            "# ==============================================================================\n",
            "!wget -qO- https://raw.githubusercontent.com/VG31OP/byrehasira-arcvision/main/scripts/colab_bootstrap.sh | bash\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "---\n",
            "### 🛠️ Optional Process Utilities (Run in a separate cell if needed)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Tail live backend logs\n",
            "!tail -n 30 /tmp/arcvision_backend.log\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Tail live frontend logs\n",
            "!tail -n 30 /tmp/arcvision_frontend.log\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# View GPU utilization\n",
            "!nvidia-smi\n"
        ]
    }
]

notebook_json = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "name": "ARC_VISION_Colab_One_Click.ipynb",
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
