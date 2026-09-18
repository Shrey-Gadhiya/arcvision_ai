from typing import List, Optional, Dict, Any
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_, and_

from app.core.database import get_db
from app.models.user import UserRole
from app.models.face import (
    FaceIdentity,
    FaceRecord,
    FaceWatchlistCategory,
    FaceWatchlistPriority,
    FaceMatchStatus
)
from app.models.audit import AuditLog, AuditAction
from app.schemas.all_schemas import (
    FaceIdentityCreate,
    FaceIdentityUpdate,
    FaceIdentityResponse,
    FaceEnrollmentRequest,
    FaceEnrollmentResponse,
    FaceRecordResponse,
    FaceRecordPaginatedResponse,
    FaceSearchQuery,
    FaceStatusResponse
)
from app.api.v1.auth import get_current_user, require_roles
from app.services.ai.face.service import face_service

router = APIRouter(prefix="/face", tags=["Face Intelligence"])

def _format_identity_response(ident: FaceIdentity) -> FaceIdentityResponse:
    emb_count = 0
    if ident.embeddings_json:
        try:
            parsed = json.loads(ident.embeddings_json)
            if isinstance(parsed, list):
                emb_count = len(parsed)
        except Exception:
            pass

    return FaceIdentityResponse(
        id=ident.id,
        name=ident.name,
        identifier=ident.identifier,
        unique_person_id=getattr(ident, 'unique_person_id', None) or (f"PERS-{ident.id:04d}" if ident.id else None),
        notes=ident.notes,
        watchlist_category=ident.watchlist_category.value if ident.watchlist_category else "CUSTOM",
        watchlist_priority=ident.watchlist_priority.value if ident.watchlist_priority else "LOW",
        is_active=ident.is_active,
        embedding_count=emb_count,
        reference_image_path=ident.reference_image_path,
        created_by=ident.created_by,
        created_at=ident.created_at,
        updated_at=ident.updated_at
    )

def _format_record_response(rec: FaceRecord) -> FaceRecordResponse:
    bbox = [0, 0, 0, 0]
    if getattr(rec, 'bbox_json', None):
        try:
            parsed = json.loads(rec.bbox_json)
            if isinstance(parsed, list) and len(parsed) >= 4:
                bbox = parsed[:4]
        except Exception:
            pass

    return FaceRecordResponse(
        id=rec.id,
        camera_id=rec.camera_id,
        track_id=rec.track_id,
        unique_person_id=getattr(rec, 'unique_person_id', None) or f"PERSON-{rec.id + 1000}",
        identity_id=rec.identity_id,
        identity_name=getattr(rec, 'matched_person_name', None),
        match_status=rec.match_status.value if rec.match_status else "UNKNOWN",
        similarity_score=rec.similarity_score or 0.0,
        recognition_threshold=0.58,
        watchlist_category=rec.watchlist_category,
        watchlist_priority=rec.watchlist_priority,
        bbox_x1=bbox[0],
        bbox_y1=bbox[1],
        bbox_x2=bbox[2],
        bbox_y2=bbox[3],
        quality_score=rec.quality_score or 0.80,
        sharpness_score=50.0,
        diagnostics="Accurate person face match",
        crop_path=rec.crop_path,
        full_frame_path=rec.full_frame_path,
        evidence_id=rec.evidence_id,
        recording_segment_id=rec.recording_segment_id,
        detector_model="YuNet/Haar-Person-Detector",
        embedding_model="Sobel-Spatial-Embedder",
        timestamp=rec.timestamp
    )

@router.get("/status", response_model=FaceStatusResponse)
async def get_face_engine_status(
    current_user = Depends(get_current_user)
):
    """Returns AI model telemetry, detection latency, embedding dimension, and gallery stats."""
    return face_service.get_status()

@router.get("/identities", response_model=List[FaceIdentityResponse])
async def list_face_identities(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lists registered face identities (excludes raw embedding vectors)."""
    query = select(FaceIdentity).order_by(desc(FaceIdentity.updated_at))
    if category:
        query = query.where(FaceIdentity.watchlist_category == FaceWatchlistCategory(category))
    if is_active is not None:
        query = query.where(FaceIdentity.is_active == is_active)
    if search:
        s = f"%{search.strip()}%"
        query = query.where(or_(FaceIdentity.name.ilike(s), FaceIdentity.identifier.ilike(s)))

    result = await db.execute(query)
    identities = result.scalars().all()
    return [_format_identity_response(i) for i in identities]

@router.post("/identities", response_model=FaceIdentityResponse, status_code=status.HTTP_201_CREATED)
async def create_face_identity(
    data: FaceIdentityCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.INVESTIGATOR]))
):
    """Manually creates an identity entry in the biometric directory."""
    cat_enum = FaceWatchlistCategory(data.watchlist_category) if data.watchlist_category in [e.value for e in FaceWatchlistCategory] else FaceWatchlistCategory.CUSTOM
    pri_enum = FaceWatchlistPriority(data.watchlist_priority) if data.watchlist_priority in [e.value for e in FaceWatchlistPriority] else FaceWatchlistPriority.LOW

    identity = FaceIdentity(
        name=data.name.strip(),
        identifier=data.identifier.strip() if data.identifier else None,
        notes=data.notes.strip() if data.notes else None,
        watchlist_category=cat_enum,
        watchlist_priority=pri_enum,
        is_active=data.is_active,
        created_by=current_user.username,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(identity)
    await db.flush()

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.CREATE,
        resource_type="FACE_IDENTITY",
        resource_id=str(identity.id),
        details_json=json.dumps({"description": f"Created identity {identity.name} ({cat_enum.value})"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(identity)

    await face_service.ensure_gallery_loaded(force_reload=True)
    return _format_identity_response(identity)

@router.get("/identities/{identity_id}", response_model=FaceIdentityResponse)
async def get_face_identity(
    identity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fetches details for a single identity."""
    res = await db.execute(select(FaceIdentity).where(FaceIdentity.id == identity_id))
    identity = res.scalars().first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    return _format_identity_response(identity)

@router.patch("/identities/{identity_id}", response_model=FaceIdentityResponse)
async def update_face_identity(
    identity_id: int,
    data: FaceIdentityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.INVESTIGATOR]))
):
    """Updates identity details, category, or active status."""
    res = await db.execute(select(FaceIdentity).where(FaceIdentity.id == identity_id))
    identity = res.scalars().first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    if data.name is not None:
        identity.name = data.name.strip()
    if data.identifier is not None:
        identity.identifier = data.identifier.strip()
    if data.notes is not None:
        identity.notes = data.notes.strip()
    if data.watchlist_category is not None:
        identity.watchlist_category = FaceWatchlistCategory(data.watchlist_category)
    if data.watchlist_priority is not None:
        identity.watchlist_priority = FaceWatchlistPriority(data.watchlist_priority)
    if data.is_active is not None:
        identity.is_active = data.is_active

    identity.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.UPDATE,
        resource_type="FACE_IDENTITY",
        resource_id=str(identity.id),
        details_json=json.dumps({"description": f"Updated identity {identity.name}"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(identity)

    await face_service.ensure_gallery_loaded(force_reload=True)
    return _format_identity_response(identity)

@router.delete("/identities/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_face_identity(
    identity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """Soft deletes or deactivates an enrolled face identity."""
    res = await db.execute(select(FaceIdentity).where(FaceIdentity.id == identity_id))
    identity = res.scalars().first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    identity.is_active = False
    identity.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.DELETE,
        resource_type="FACE_IDENTITY",
        resource_id=str(identity.id),
        details_json=json.dumps({"description": f"Deactivated face identity {identity.name}"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()

    await face_service.ensure_gallery_loaded(force_reload=True)
    return None

@router.post("/enroll", response_model=FaceEnrollmentResponse)
async def enroll_face_biometric(
    data: FaceEnrollmentRequest,
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.INVESTIGATOR]))
):
    """
    Executes full quality-gated face enrollment.
    Validates single face, resolution, blur, and generates normalized embedding.
    """
    result = await face_service.enroll_identity(
        name=data.name,
        identifier=data.identifier,
        image_base64=data.image_base64,
        watchlist_category=data.watchlist_category or "CUSTOM",
        watchlist_priority=data.watchlist_priority or "LOW",
        notes=data.notes,
        created_by=current_user.username
    )

    if not result.get("success"):
        return FaceEnrollmentResponse(
            success=False,
            error=result.get("error"),
            quality_score=result.get("quality_score", 0.0),
            sharpness_score=result.get("sharpness_score", 0.0),
            diagnostics=result.get("diagnostics", "Enrollment failed"),
            embedding_generated=False
        )

    return FaceEnrollmentResponse(
        success=True,
        identity_id=result.get("identity_id"),
        name=result.get("name"),
        quality_score=result.get("quality_score", 0.0),
        sharpness_score=result.get("sharpness_score", 0.0),
        diagnostics=result.get("diagnostics", "Enrollment completed successfully"),
        embedding_generated=True
    )

@router.get("/records", response_model=FaceRecordPaginatedResponse)
async def list_face_records(
    camera_id: Optional[int] = None,
    identity_id: Optional[int] = None,
    match_status: Optional[str] = None,
    min_similarity: Optional[float] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Retrieves paginated face detection & recognition sightings."""
    query = select(FaceRecord)
    count_query = select(func.count(FaceRecord.id))

    filters = []
    if camera_id is not None:
        filters.append(FaceRecord.camera_id == camera_id)
    if identity_id is not None:
        filters.append(FaceRecord.identity_id == identity_id)
    if match_status:
        filters.append(FaceRecord.match_status == FaceMatchStatus(match_status))
    if min_similarity is not None:
        filters.append(FaceRecord.similarity_score >= min_similarity)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(desc(FaceRecord.timestamp)).offset(offset).limit(limit)
    res = await db.execute(query)
    records = res.scalars().all()

    return FaceRecordPaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[_format_record_response(r) for r in records]
    )

@router.post("/search", response_model=FaceRecordPaginatedResponse)
async def search_face_records(
    criteria: FaceSearchQuery,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Multi-criteria forensic search for face sightings across identities, timeframes, and cameras."""
    query = select(FaceRecord)
    count_query = select(func.count(FaceRecord.id))

    filters = []
    if criteria.identity_id is not None:
        filters.append(FaceRecord.identity_id == criteria.identity_id)
    if criteria.unique_person_id:
        uid_s = f"%{criteria.unique_person_id.strip()}%"
        filters.append(or_(FaceRecord.unique_person_id.ilike(uid_s), FaceRecord.identity_name.ilike(uid_s)))
    if criteria.name:
        filters.append(FaceRecord.identity_name.ilike(f"%{criteria.name.strip()}%"))
    if criteria.match_status:
        filters.append(FaceRecord.match_status == FaceMatchStatus(criteria.match_status))
    if criteria.watchlist_category:
        filters.append(FaceRecord.watchlist_category == FaceWatchlistCategory(criteria.watchlist_category))
    if criteria.camera_id is not None:
        filters.append(FaceRecord.camera_id == criteria.camera_id)
    if criteria.min_similarity is not None:
        filters.append(FaceRecord.similarity_score >= criteria.min_similarity)
    if criteria.start_time:
        filters.append(FaceRecord.timestamp >= criteria.start_time)
    if criteria.end_time:
        filters.append(FaceRecord.timestamp <= criteria.end_time)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(desc(FaceRecord.timestamp)).offset(criteria.offset).limit(criteria.limit)
    res = await db.execute(query)
    records = res.scalars().all()

    # Log search audit
    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.EXPORT,
        resource_type="FACE_SEARCH",
        resource_id="0",
        details_json=json.dumps({"description": f"Forensic face query executed (total hits: {total})"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()

    return FaceRecordPaginatedResponse(
        total=total,
        limit=criteria.limit,
        offset=criteria.offset,
        items=[_format_record_response(r) for r in records]
    )

@router.get("/watchlist", response_model=List[FaceIdentityResponse])
async def list_face_watchlist(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lists all active watchlist targets (WATCH, ALERT, ALLOW, CUSTOM)."""
    query = select(FaceIdentity).where(FaceIdentity.is_active == True)
    if category:
        query = query.where(FaceIdentity.watchlist_category == FaceWatchlistCategory(category))

    result = await db.execute(query.order_by(desc(FaceIdentity.updated_at)))
    identities = result.scalars().all()
    return [_format_identity_response(i) for i in identities]
