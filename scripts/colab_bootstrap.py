import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    repo_url = os.getenv("REPO_URL", "https://github.com/VG31OP/byrehasira-arcvision.git")
    branch = os.getenv("BRANCH", "main")
    
    if os.path.exists("/kaggle/working"):
        repo_dir = Path(os.getenv("REPO_DIR", "/kaggle/working/ARCVISION"))
    else:
        repo_dir = Path(os.getenv("REPO_DIR", "/content/ARCVISION"))

    print("=" * 70)
    print("  🛰️ ARC VISION — ONE-COMMAND BOOTSTRAPPER (PYTHON RUNTIME)")
    print("=" * 70)
    print(f"Target Repository : {repo_url}")
    print(f"Target Branch     : {branch}")
    print(f"Target Directory  : {repo_dir}")
    print("=" * 70)

    # Clean stale temporary directories
    for temp_path in ["/tmp/ARCVISION_REPO", "/tmp/arcvision_logs"]:
        try:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)
        except Exception:
            pass

    # Clone or Update Repository
    if not repo_dir.exists():
        print(f"[ARC VISION] Cloning repository into {repo_dir}...")
        subprocess.run(["git", "clone", "--quiet", repo_url, str(repo_dir)], check=True)
    else:
        print(f"[ARC VISION] Updating existing repository at {repo_dir}...")
        subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=str(repo_dir), capture_output=True)
        subprocess.run(["git", "fetch", "origin", branch, "--quiet"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "reset", "--hard", f"origin/{branch}", "--quiet"], cwd=str(repo_dir), check=True)

    os.chdir(str(repo_dir))
    
    # Launch Master Launcher
    launcher_path = repo_dir / "scripts" / "colab_launch.py"
    print(f"[ARC VISION] Launching Master Controller via {sys.executable}...")
    subprocess.run([sys.executable, str(launcher_path)], cwd=str(repo_dir), check=True)

if __name__ == "__main__":
    main()
