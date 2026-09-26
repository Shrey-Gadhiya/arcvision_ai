import os
import time
import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.config import settings
from app.models.evidence import Evidence, EvidenceType
from app.models.audit import AuditLog
from app.schemas.all_schemas import (
    EvidenceResponse,
    EvidencePackageExportResponse,
    EvidencePackageVerifyRequest,
    EvidencePackageVerifyResponse
)
from app.services.evidence_manager import evidence_manager, compute_sha256

logger = logging.getLogger("arc_vision.evidence_api")

router = APIRouter(prefix="/evidence", tags=["Evidence Locker & Forensics"])

def _resolve_evidence_disk_path(file_path_str: str) -> Optional[Path]:
    if not file_path_str:
        return None
    # Strip URL prefixes
    clean_p = file_path_str.replace("/static/", "").lstrip("/").replace("\\", "/")
    
    candidates = [
        Path(file_path_str),
        settings.DATA_DIR / clean_p,
        Path("data") / clean_p,
        settings.EVIDENCE_DIR / Path(file_path_str).name,
        settings.SNAPSHOTS_DIR / "anpr" / Path(file_path_str).name,
        settings.SNAPSHOTS_DIR / "faces" / Path(file_path_str).name,
        settings.SNAPSHOTS_DIR / Path(file_path_str).name,
        settings.UPLOADS_DIR / Path(file_path_str).name,
        settings.RECORDINGS_DIR / Path(file_path_str).name,
    ]
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c.resolve()
        except Exception:
            pass
    return None

@router.get("/", response_model=List[EvidenceResponse])
async def list_evidence(
    incident_id: Optional[int] = None,
    camera_id: Optional[int] = None,
    file_type: Optional[EvidenceType] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    query = select(Evidence).order_by(desc(Evidence.created_at))
    if incident_id:
        query = query.where(Evidence.incident_id == incident_id)
    if camera_id:
        query = query.where(Evidence.camera_id == camera_id)
    if file_type:
        query = query.where(Evidence.file_type == file_type)

    result = await db.execute(query.limit(limit))
    return result.scalars().all()

@router.get("/file/{filename}")
async def get_evidence_file(filename: str):
    disk_path = _resolve_evidence_disk_path(filename)
    if not disk_path or not disk_path.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found")

    media_type = "video/mp4" if filename.endswith(".mp4") else "image/jpeg"
    return FileResponse(path=str(disk_path), media_type=media_type, filename=filename)

@router.post("/{evidence_id}/verify")
async def verify_evidence_integrity(evidence_id: int, db: AsyncSession = Depends(get_db)):
    """
    Forensic Tamper Verification: Recomputes the SHA-256 hash of the evidence
    file from physical storage and compares it with the database cryptographic record.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence record not found")

    disk_path = _resolve_evidence_disk_path(evidence.file_path)
    if not disk_path or not disk_path.exists():
        raise HTTPException(status_code=404, detail=f"Underlying media file missing from disk storage ({evidence.file_path})")

    current_hash = compute_sha256(disk_path)
    is_tamper_free = (current_hash == evidence.sha256_hash) if evidence.sha256_hash else True

    # Log audit
    audit = AuditLog(
        username="investigator",
        user_role="INVESTIGATOR",
        action="VERIFY_EVIDENCE",
        resource_type="EVIDENCE",
        resource_id=str(evidence.id),
        details_json=json.dumps({"tamper_free": is_tamper_free, "sha256": current_hash})
    )
    db.add(audit)
    await db.commit()

    return {
        "evidence_id": evidence.id,
        "filename": disk_path.name,
        "recorded_sha256": evidence.sha256_hash or current_hash,
        "current_disk_sha256": current_hash,
        "integrity_verified": is_tamper_free,
        "tamper_detected": not is_tamper_free,
        "file_size_bytes": disk_path.stat().st_size
    }

@router.post("/verify-all")
async def verify_all_evidence(db: AsyncSession = Depends(get_db)):
    """
    Batch Cryptographic Verification: Computes SHA-256 for all stored forensic items
    and returns chain-of-custody audit report.
    """
    result = await db.execute(select(Evidence).order_by(desc(Evidence.created_at)).limit(100))
    items = result.scalars().all()

    verified_count = 0
    tampered_count = 0
    missing_count = 0
    results = []

    for ev in items:
        disk_path = _resolve_evidence_disk_path(ev.file_path)
        if not disk_path or not disk_path.exists():
            missing_count += 1
            results.append({
                "evidence_id": ev.id,
                "file_path": ev.file_path,
                "file_exists": False,
                "is_valid": False,
                "status": "MISSING_ON_DISK",
                "calculated_sha256": None
            })
            continue

        c_hash = compute_sha256(disk_path)
        ok = (c_hash == ev.sha256_hash) if ev.sha256_hash else True
        if ok:
            verified_count += 1
        else:
            tampered_count += 1

        results.append({
            "evidence_id": ev.id,
            "filename": disk_path.name,
            "file_exists": True,
            "is_valid": ok,
            "status": "VERIFIED" if ok else "TAMPER_DETECTED",
            "calculated_sha256": c_hash
        })

    return {
        "total_checked": len(items),
        "valid_count": verified_count,
        "verified_authentic": verified_count,
        "tampered_count": tampered_count,
        "tamper_detected": tampered_count,
        "missing_count": missing_count,
        "missing_files": missing_count,
        "audit_timestamp": time.time(),
        "results": results
    }

@router.post("/export-package/{incident_id}", response_model=EvidencePackageExportResponse)
async def export_evidence_package(
    incident_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a read-only, tamper-evident ZIP evidence package containing:
    incident metadata, snapshots, video clips, and cryptographic manifest.json.
    Automatically marks associated segments as is_protected=True.
    """
    try:
        pkg = await evidence_manager.export_incident_evidence_package(
            incident_id=incident_id,
            session=db,
            investigator="investigator"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Audit log
    audit = AuditLog(
        username="investigator",
        user_role="INVESTIGATOR",
        action="EXPORT_EVIDENCE_PACKAGE",
        resource_type="INCIDENT",
        resource_id=str(incident_id),
        details_json=json.dumps({"package": pkg["package_filename"], "sha256": pkg["sha256_hash"]})
    )
    db.add(audit)
    await db.commit()

    return pkg

@router.get("/packages/{filename}")
async def download_evidence_package(filename: str):
    """Downloads an exported evidence package ZIP archive."""
    pkg_dir = settings.EVIDENCE_DIR / "packages"
    file_path = _validate_safe_evidence_path(filename, pkg_dir)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence package not found")

    return FileResponse(
        path=str(file_path),
        media_type="application/zip",
        filename=filename
    )

@router.post("/verify-package", response_model=EvidencePackageVerifyResponse)
async def verify_evidence_package_endpoint(
    payload: EvidencePackageVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validates the integrity of an exported evidence ZIP package by recalculating
    SHA-256 hashes for all bundled files and verifying against manifest.json.
    """
    try:
        res = evidence_manager.verify_evidence_package(payload.package_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Package {payload.package_filename} not found")

    # Audit log
    audit = AuditLog(
        username="investigator",
        user_role="INVESTIGATOR",
        action="VERIFY_EVIDENCE_PACKAGE",
        resource_type="EVIDENCE_PACKAGE",
        resource_id=payload.package_filename,
        details_json=json.dumps({"is_valid": res["is_valid"], "status": res["status"]})
    )
    db.add(audit)
    await db.commit()

    return res

