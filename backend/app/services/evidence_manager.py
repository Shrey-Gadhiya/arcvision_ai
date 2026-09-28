import os
import cv2
import time
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from app.core.config import settings

logger = logging.getLogger("arc_vision.evidence")

def compute_sha256(file_path: Path | str) -> str:
    """Computes tamper-evident SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

from collections import deque

class CameraRingBuffer:
    def __init__(self, max_seconds: int = 12, fps: int = 15):
        self.max_frames = max_seconds * fps
        self.buffer = deque(maxlen=self.max_frames) # [(timestamp, frame)]

    def add_frame(self, frame: np.ndarray):
        now = time.time()
        # Keep lightweight frame in ring buffer (max 960px width) to avoid memory thrashing
        h, w = frame.shape[:2]
        if w > 960:
            scale_w = 960
            scale_h = int(960 * h / w)
            buf_f = cv2.resize(frame, (scale_w, scale_h))
        else:
            buf_f = frame
        self.buffer.append((now, buf_f))

    def get_frames(self) -> List[Tuple[float, np.ndarray]]:
        return list(self.buffer)

class EvidenceManager:
    def __init__(self):
        self.evidence_dir = settings.EVIDENCE_DIR
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.ring_buffers: Dict[int, CameraRingBuffer] = {}

    def register_camera(self, camera_id: int, fps: int = 15):
        if camera_id not in self.ring_buffers:
            self.ring_buffers[camera_id] = CameraRingBuffer(
                max_seconds=settings.RING_BUFFER_SECONDS,
                fps=fps
            )

    def buffer_frame(self, camera_id: int, frame: np.ndarray):
        if camera_id not in self.ring_buffers:
            self.register_camera(camera_id)
        self.ring_buffers[camera_id].add_frame(frame)

    def save_snapshot(
        self,
        camera_id: int,
        frame: np.ndarray,
        incident_code: str
    ) -> Dict[str, Any]:
        """Saves a high-res JPEG snapshot and computes its SHA-256 hash."""
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"snap_{incident_code}_{camera_id}_{timestamp_str}.jpg"
        file_path = self.evidence_dir / filename

        cv2.imwrite(str(file_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        file_hash = compute_sha256(file_path)
        file_size = file_path.stat().st_size

        return {
            "file_type": "SNAPSHOT",
            "file_path": f"/evidence/{filename}",
            "absolute_path": str(file_path),
            "file_size_bytes": file_size,
            "sha256_hash": file_hash,
            "metadata": {
                "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
                "timestamp": timestamp_str
            }
        }

    def save_crop(
        self,
        frame: np.ndarray,
        box: List[float], # [x1, y1, x2, y2] normalized
        crop_type: str,
        prefix: str = "target"
    ) -> Optional[Dict[str, Any]]:
        """Crops object region (person, vehicle, plate, face) and saves it."""
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]
        x1 = max(0, int(box[0] * w))
        y1 = max(0, int(box[1] * h))
        x2 = min(w, int(box[2] * w))
        y2 = min(h, int(box[3] * h))

        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"crop_{crop_type.lower()}_{prefix}_{timestamp_str}.jpg"
        file_path = self.evidence_dir / filename

        cv2.imwrite(str(file_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        file_hash = compute_sha256(file_path)

        return {
            "file_type": crop_type,
            "file_path": f"/evidence/{filename}",
            "absolute_path": str(file_path),
            "file_size_bytes": file_path.stat().st_size,
            "sha256_hash": file_hash,
            "metadata": {
                "crop_box": [x1, y1, x2, y2],
                "resolution": f"{crop.shape[1]}x{crop.shape[0]}"
            }
        }

    def save_incident_clip(
        self,
        camera_id: int,
        incident_code: str,
        fps: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts pre-event buffer frames and compiles them into a standard MP4 video clip.
        """
        if camera_id not in self.ring_buffers:
            return None

        frames = self.ring_buffers[camera_id].get_frames()
        if not frames or len(frames) < 5:
            return None

        first_frame = frames[0][1]
        h, w = first_frame.shape[:2]

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"clip_{incident_code}_{camera_id}_{timestamp_str}.mp4"
        file_path = self.evidence_dir / filename

        # Use 'mp4v' or 'avc1'
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(file_path), fourcc, fps, (w, h))

        for _, f in frames:
            out.write(f)
        out.release()

        file_hash = compute_sha256(file_path)
        file_size = file_path.stat().st_size

        return {
            "file_type": "CLIP",
            "file_path": f"/evidence/{filename}",
            "absolute_path": str(file_path),
            "file_size_bytes": file_size,
            "sha256_hash": file_hash,
            "metadata": {
                "fps": fps,
                "duration_sec": round(len(frames) / fps, 1),
                "frame_count": len(frames),
                "resolution": f"{w}x{h}"
            }
        }

    async def export_incident_evidence_package(
        self,
        incident_id: int,
        session,
        investigator: str = "investigator"
    ) -> Dict[str, Any]:
        """
        Constructs a complete tamper-evident forensic evidence ZIP package for an incident.
        Bundles incident report JSON, snapshots, video clips, and cryptographic manifest.json.
        Marks all bundled recording segments and evidence as is_protected=True.
        """
        import zipfile
        from sqlalchemy import select
        from app.models.incident import Incident
        from app.models.camera import Camera
        from app.models.evidence import Evidence
        from app.models.recording import RecordingSegment

        # 1. Fetch Incident & Camera
        inc_res = await session.execute(select(Incident).where(Incident.id == incident_id))
        incident = inc_res.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident #{incident_id} not found")

        cam_res = await session.execute(select(Camera).where(Camera.id == incident.camera_id))
        camera = cam_res.scalar_one_or_none()
        cam_name = camera.name if camera else f"Camera #{incident.camera_id}"

        # 2. Fetch Evidence items linked to this incident
        evi_res = await session.execute(select(Evidence).where(Evidence.incident_id == incident.id))
        evidence_items = evi_res.scalars().all()

        # 3. Create Packages directory
        packages_dir = self.evidence_dir / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)
        pkg_filename = f"evidence_package_{incident.incident_code}.zip"
        pkg_path = packages_dir / pkg_filename

        manifest_files = []

        # Create temporary zip archive
        with zipfile.ZipFile(str(pkg_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # A. Write incident_report.json
            report_data = {
                "incident_id": incident.id,
                "incident_code": incident.incident_code,
                "title": incident.title,
                "summary": incident.summary,
                "incident_type": incident.incident_type,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "threat_score": incident.threat_score,
                "location_name": incident.location_name,
                "camera": {
                    "id": camera.id if camera else incident.camera_id,
                    "name": cam_name,
                    "group_name": camera.group_name if camera else "DEFAULT",
                    "location": camera.location if camera else "Unknown"
                },
                "timestamps": {
                    "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                    "triaged_at": incident.triaged_at.isoformat() if incident.triaged_at else None,
                    "acknowledged_at": incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                    "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                    "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
                },
                "transition_history": json.loads(incident.transition_history_json) if incident.transition_history_json else [],
                "operator_notes": json.loads(incident.operator_notes_json) if incident.operator_notes_json else [],
                "tags": json.loads(incident.tags_json) if incident.tags_json else []
            }
            report_bytes = json.dumps(report_data, indent=2).encode("utf-8")
            report_hash = hashlib.sha256(report_bytes).hexdigest()
            zf.writestr("incident_report.json", report_bytes)
            manifest_files.append({
                "path": "incident_report.json",
                "file_type": "METADATA_JSON",
                "file_size_bytes": len(report_bytes),
                "sha256_hash": report_hash
            })

            # B. Add snapshots and clips from Evidence table
            for ev in evidence_items:
                fname = Path(ev.file_path).name
                disk_f = self.evidence_dir / fname
                if disk_f.exists():
                    subfolder = "video" if ev.file_type.value == "CLIP" else "snapshots"
                    arc_path = f"{subfolder}/{fname}"
                    zf.write(str(disk_f), arcname=arc_path)
                    f_hash = compute_sha256(disk_f)
                    manifest_files.append({
                        "path": arc_path,
                        "file_type": ev.file_type.value,
                        "file_size_bytes": disk_f.stat().st_size,
                        "sha256_hash": f_hash
                    })

            # C. Create manifest.json
            now_iso = datetime.now(timezone.utc).isoformat()
            manifest_content = {
                "incident_id": incident.id,
                "incident_code": incident.incident_code,
                "camera_id": incident.camera_id,
                "camera_name": cam_name,
                "generated_at": now_iso,
                "generated_by": investigator,
                "summary": incident.summary,
                "threat_score": incident.threat_score,
                "total_files": len(manifest_files),
                "files": manifest_files
            }
            # Compute signature of all file hashes concatenated
            all_hashes_concat = "".join(f["sha256_hash"] for f in sorted(manifest_files, key=lambda x: x["path"]))
            manifest_sig = hashlib.sha256(all_hashes_concat.encode("utf-8")).hexdigest()
            manifest_content["manifest_signature"] = manifest_sig

            manifest_bytes = json.dumps(manifest_content, indent=2).encode("utf-8")
            zf.writestr("manifest.json", manifest_bytes)

        # 4. Protect all linked recording segments for this camera around detection time
        if incident.detected_at:
            from datetime import timedelta
            start_window = incident.detected_at - timedelta(seconds=60)
            end_window = incident.detected_at + timedelta(seconds=60)
            seg_stmt = select(RecordingSegment).where(
                RecordingSegment.camera_id == incident.camera_id,
                RecordingSegment.end_time >= start_window,
                RecordingSegment.start_time <= end_window
            )
            seg_res = await session.execute(seg_stmt)
            for seg in seg_res.scalars().all():
                seg.is_protected = True

        await session.commit()

        pkg_size = pkg_path.stat().st_size
        pkg_hash = compute_sha256(pkg_path)

        return {
            "package_filename": pkg_filename,
            "download_url": f"/evidence/packages/{pkg_filename}",
            "file_size_bytes": pkg_size,
            "sha256_hash": pkg_hash,
            "total_files": len(manifest_files) + 1,
            "is_protected": True,
            "manifest": manifest_content
        }

    def verify_evidence_package(self, package_filename: str) -> Dict[str, Any]:
        """
        Performs deep cryptographic verification of an evidence package ZIP.
        Extracts and recalculates SHA-256 for each bundled file, verifying against manifest.json.
        """
        import zipfile
        packages_dir = self.evidence_dir / "packages"
        pkg_path = packages_dir / package_filename

        if not pkg_path.exists():
            raise FileNotFoundError(f"Evidence package {package_filename} not found")

        with zipfile.ZipFile(str(pkg_path), "r") as zf:
            if "manifest.json" not in zf.namelist():
                return {
                    "package_filename": package_filename,
                    "is_valid": False,
                    "status": "CORRUPTED_MISSING_MANIFEST",
                    "verified_files_count": 0,
                    "tampered_files": ["manifest.json"],
                    "recorded_manifest_hash": "",
                    "calculated_manifest_hash": ""
                }

            manifest_raw = zf.read("manifest.json").decode("utf-8")
            manifest = json.loads(manifest_raw)

            tampered = []
            verified_count = 0
            computed_hashes = []

            for f_entry in manifest.get("files", []):
                arc_p = f_entry["path"]
                if arc_p not in zf.namelist():
                    tampered.append(f"{arc_p} (Missing from ZIP)")
                    continue

                f_bytes = zf.read(arc_p)
                computed_h = hashlib.sha256(f_bytes).hexdigest()
                computed_hashes.append((arc_p, computed_h))

                if computed_h != f_entry["sha256_hash"]:
                    tampered.append(f"{arc_p} (Hash mismatch: expected {f_entry['sha256_hash'][:8]}..., got {computed_h[:8]}...)")
                else:
                    verified_count += 1

            # Check signature
            computed_hashes_concat = "".join(h for _, h in sorted(computed_hashes, key=lambda x: x[0]))
            calc_sig = hashlib.sha256(computed_hashes_concat.encode("utf-8")).hexdigest()
            recorded_sig = manifest.get("manifest_signature", "")

            is_valid = (len(tampered) == 0) and (calc_sig == recorded_sig)
            status_text = "VERIFIED_TAMPER_FREE" if is_valid else "TAMPER_DETECTED"

            return {
                "package_filename": package_filename,
                "is_valid": is_valid,
                "status": status_text,
                "verified_files_count": verified_count,
                "tampered_files": tampered,
                "recorded_manifest_hash": recorded_sig,
                "calculated_manifest_hash": calc_sig
            }

evidence_manager = EvidenceManager()

