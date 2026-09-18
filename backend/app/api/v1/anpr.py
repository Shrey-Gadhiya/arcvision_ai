from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.models.anpr import (
    ANPRRecord,
    ANPRWatchlist,
    PlateWatchlistCategory,
    WatchlistPriority,
    PlateValidationStatus
)
from app.models.audit import AuditLog
from app.schemas.all_schemas import (
    ANPRRecordResponse,
    ANPRRecordPaginatedResponse,
    ANPRWatchlistCreate,
    ANPRWatchlistUpdate,
    ANPRWatchlistResponse,
    PlateSearchQuery,
    PlateQueryResult,
    VehicleIntelligenceStats,
    ANPRStatusResponse,
    ANPRCaptureRequest,
    ANPRCaptureResponse
)
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user, require_roles
from app.services.ai.anpr.service import anpr_service
from app.services.ai.anpr.normalizer import clean_raw_plate, normalize_indian_plate
from app.services.ai.anpr.validators import IndianPlateValidator
from app.services.analytics.vehicle_intelligence import vehicle_intelligence

router = APIRouter(prefix="/anpr", tags=["ANPR & Vehicle Intelligence"])

@router.get("/status", response_model=ANPRStatusResponse)
async def get_anpr_status():
    """Returns engine health, adapter status, and validation capabilities."""
    return anpr_service.get_status()

@router.post("/capture-and-detect", response_model=ANPRCaptureResponse)
async def capture_and_detect_plate(
    payload: ANPRCaptureRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Forensic Vehicle Number Plate Capture & Neural Recognition.
    Accepts snapshot image/frame, localizes license plate, extracts characters with EasyOCR,
    validates RTO pattern, matches against watchlist, and stores dual/triple snapshots.
    """
    result = await anpr_service.capture_and_detect_plate(
        image_data=payload.image_base64,
        camera_id=payload.camera_id,
        camera_name=payload.camera_name,
        notes=payload.notes
    )
    return result

@router.get("/records", response_model=ANPRRecordPaginatedResponse)
async def list_anpr_records(
    camera_id: Optional[int] = None,
    plate_number: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    is_matched: Optional[bool] = None,
    validation_status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Returns paginated ANPR plate sightings with filtering."""
    query = select(ANPRRecord)

    if camera_id is not None:
        query = query.where(ANPRRecord.camera_id == camera_id)
    if plate_number:
        clean = clean_raw_plate(plate_number)
        query = query.where(ANPRRecord.plate_number.like(f"%{clean}%"))
    if vehicle_type:
        query = query.where(ANPRRecord.vehicle_type == vehicle_type.lower())
    if is_matched is not None:
        query = query.where(ANPRRecord.is_matched == is_matched)
    if validation_status:
        try:
            val_enum = PlateValidationStatus(validation_status.upper())
            query = query.where(ANPRRecord.validation_status == val_enum)
        except ValueError:
            pass
    if start_time:
        query = query.where(ANPRRecord.timestamp >= start_time)
    if end_time:
        query = query.where(ANPRRecord.timestamp <= end_time)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(desc(ANPRRecord.timestamp)).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": records
    }

@router.get("/records/{record_id}", response_model=ANPRRecordResponse)
async def get_anpr_record(record_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches full details for a single plate sighting."""
    result = await db.execute(select(ANPRRecord).where(ANPRRecord.id == record_id))
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="ANPR sighting record not found")
    return record

@router.post("/search", response_model=ANPRRecordPaginatedResponse)
async def search_plates(query_data: PlateSearchQuery, db: AsyncSession = Depends(get_db)):
    """Multi-criteria forensic plate search."""
    return await list_anpr_records(
        camera_id=query_data.camera_id,
        plate_number=query_data.plate_number,
        vehicle_type=query_data.vehicle_type,
        is_matched=query_data.is_matched,
        validation_status=query_data.validation_status,
        start_time=query_data.start_time,
        end_time=query_data.end_time,
        limit=query_data.limit,
        offset=query_data.offset,
        db=db
    )

@router.get("/query/{plate_number}", response_model=PlateQueryResult)
async def query_plate(plate_number: str, db: AsyncSession = Depends(get_db)):
    """Looks up sightings history, validation status, and watchlist flags for a plate number."""
    clean = clean_raw_plate(plate_number)
    normalized, _ = normalize_indian_plate(clean)
    validation = IndianPlateValidator.validate(normalized)

    # History sightings
    result = await db.execute(
        select(ANPRRecord).where(
            ANPRRecord.plate_number.like(f"%{clean}%")
        ).order_by(desc(ANPRRecord.timestamp)).limit(50)
    )
    records = result.scalars().all()

    # Watchlist check
    watch_res = await db.execute(
        select(ANPRWatchlist).where(
            ANPRWatchlist.plate_number == normalized,
            ANPRWatchlist.is_active == True
        )
    )
    watch_entry = watch_res.scalars().first()

    return {
        "plate_number": plate_number,
        "normalized_plate": normalized,
        "validation_status": validation.status,
        "validation_format": validation.format_name,
        "is_flagged": watch_entry is not None,
        "watchlist_info": watch_entry,
        "sightings_count": len(records),
        "history": records
    }

@router.get("/watchlist", response_model=List[ANPRWatchlistResponse])
async def list_watchlist(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lists security watchlists with optional category/priority filtering."""
    query = select(ANPRWatchlist)
    if is_active is not None:
        query = query.where(ANPRWatchlist.is_active == is_active)
    if category:
        try:
            cat_enum = PlateWatchlistCategory(category.upper())
            query = query.where(ANPRWatchlist.category == cat_enum)
        except ValueError:
            pass
    if priority:
        try:
            pri_enum = WatchlistPriority(priority.upper())
            query = query.where(ANPRWatchlist.priority == pri_enum)
        except ValueError:
            pass

    query = query.order_by(desc(ANPRWatchlist.created_at))
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/watchlist", response_model=ANPRWatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    data: ANPRWatchlistCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.INVESTIGATOR]))
):
    """Adds a license plate to the security watchlist."""
    clean_plate, _ = normalize_indian_plate(data.plate_number)
    if not clean_plate:
        raise HTTPException(status_code=400, detail="Invalid plate number")

    existing = await db.execute(select(ANPRWatchlist).where(ANPRWatchlist.plate_number == clean_plate))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Plate number is already registered in the watchlist")

    try:
        cat_enum = PlateWatchlistCategory(data.category.upper())
    except ValueError:
        cat_enum = PlateWatchlistCategory.SUSPECT

    try:
        pri_enum = WatchlistPriority(data.priority.upper())
    except ValueError:
        pri_enum = WatchlistPriority.HIGH

    item = ANPRWatchlist(
        plate_number=clean_plate,
        category=cat_enum,
        priority=pri_enum,
        vehicle_model=data.vehicle_model,
        notes=data.notes,
        is_active=data.is_active
    )
    db.add(item)
    await db.flush()

    # Audit log
    audit = AuditLog(
        username=current_user.username if current_user else "SYSTEM",
        user_role=current_user.role.value if current_user else "SYSTEM",
        action="WATCHLIST_PLATE_ADDED",
        resource_type="ANPRWatchlist",
        resource_id=str(item.id),
        details_json=f'{{"plate": "{clean_plate}", "category": "{cat_enum.value}", "priority": "{pri_enum.value}"}}',
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/watchlist/{item_id}", response_model=ANPRWatchlistResponse)
async def update_watchlist_item(
    item_id: int,
    data: ANPRWatchlistUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.INVESTIGATOR]))
):
    """Updates category, notes, or active status of a watchlist entry."""
    result = await db.execute(select(ANPRWatchlist).where(ANPRWatchlist.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")

    if data.category:
        try:
            item.category = PlateWatchlistCategory(data.category.upper())
        except ValueError:
            pass
    if data.priority:
        try:
            item.priority = WatchlistPriority(data.priority.upper())
        except ValueError:
            pass
    if data.vehicle_model is not None:
        item.vehicle_model = data.vehicle_model
    if data.notes is not None:
        item.notes = data.notes
    if data.is_active is not None:
        item.is_active = data.is_active

    item.updated_at = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog(
        username=current_user.username if current_user else "SYSTEM",
        user_role=current_user.role.value if current_user else "SYSTEM",
        action="WATCHLIST_PLATE_UPDATED",
        resource_type="ANPRWatchlist",
        resource_id=str(item.id),
        details_json=f'{{"plate": "{item.plate_number}", "is_active": {item.is_active}}}',
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/watchlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """Deletes an entry from the security watchlist."""
    result = await db.execute(select(ANPRWatchlist).where(ANPRWatchlist.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")

    plate_num = item.plate_number
    await db.delete(item)

    # Audit log
    audit = AuditLog(
        username=current_user.username if current_user else "SYSTEM",
        user_role=current_user.role.value if current_user else "SYSTEM",
        action="WATCHLIST_PLATE_DELETED",
        resource_type="ANPRWatchlist",
        resource_id=str(item_id),
        details_json=f'{{"plate": "{plate_num}"}}',
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    return None

@router.get("/vehicles/analytics", response_model=VehicleIntelligenceStats)
async def get_vehicle_analytics(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Returns vehicle distribution, stationary count, and top plate sightings."""
    return await vehicle_intelligence.get_vehicle_analytics(db, hours=hours)
