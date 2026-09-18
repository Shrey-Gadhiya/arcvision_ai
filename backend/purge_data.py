import os
import shutil
import asyncio
from pathlib import Path
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine

async def purge_all_recordings_and_evidence():
    print("=== PURGING ALL CAPTURED RECORDINGS AND EVIDENCE ===")
    
    # 1. Purge Directories on Disk
    dirs_to_clean = [
        settings.RECORDINGS_DIR,
        settings.EVIDENCE_DIR,
        settings.SNAPSHOTS_DIR,
        settings.DATA_DIR / "snapshots" / "anpr",
        settings.DATA_DIR / "snapshots" / "faces",
        settings.DATA_DIR / "snapshots" / "crops",
        settings.DATA_DIR / "snapshots" / "segments",
        settings.DATA_DIR / "evidence" / "packages",
    ]

    total_files_deleted = 0
    total_bytes_freed = 0

    for d in dirs_to_clean:
        if d.exists():
            for root, dirs, files in os.walk(d):
                for f in files:
                    fp = Path(root) / f
                    try:
                        sz = fp.stat().st_size
                        fp.unlink()
                        total_files_deleted += 1
                        total_bytes_freed += sz
                    except Exception as e:
                        print(f"Error deleting file {fp}: {e}")
            # Also remove empty subdirectories
            for root, dirs, files in os.walk(d, topdown=False):
                for sub_d in dirs:
                    sub_p = Path(root) / sub_d
                    try:
                        sub_p.rmdir()
                    except Exception:
                        pass
        # Re-ensure base directories exist
        d.mkdir(parents=True, exist_ok=True)

    print(f"Purged {total_files_deleted} disk files ({total_bytes_freed / (1024*1024):.2f} MB freed).")

    # 2. Purge Database Tables
    tables_to_clear = [
        "recording_segments",
        "evidences",
        "evidence",
        "tracked_snapshots",
        "anpr_records",
        "face_records",
        "detection_events",
        "rule_events",
        "incidents"
    ]

    async with AsyncSessionLocal() as session:
        for tbl in tables_to_clear:
            try:
                res = await session.execute(text(f"DELETE FROM {tbl}"))
                print(f"Cleared table: {tbl}")
            except Exception as e:
                print(f"Note on clearing {tbl}: {e}")
        await session.commit()

        # Vacuum SQLite database to reclaim disk space
        try:
            await session.execute(text("VACUUM"))
            print("Database VACUUM completed.")
        except Exception as e:
            print(f"VACUUM note: {e}")

    print("=== PURGE COMPLETE: All recordings, evidence, snapshots, and logs removed. ===")

if __name__ == "__main__":
    asyncio.run(purge_all_recordings_and_evidence())
