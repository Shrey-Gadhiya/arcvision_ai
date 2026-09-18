import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func

from app.core.database import get_db
from app.models.camera import Camera
from app.models.investigation import InvestigationCase, CaseFinding, CaseStatus, CasePriority
from app.schemas.all_schemas import (
    InvestigationSearchFilter,
    InvestigationSearchResultItem,
    InvestigationSearchResponse,
    ParsedSemanticQuery,
    NLSearchRequest,
    NLSearchResponse,
    InvestigationCaseCreate,
    InvestigationCaseUpdate,
    InvestigationCaseResponse,
    InvestigationCaseListResponse,
    CaseFindingCreate,
    CaseFindingResponse,
    CaseTimelineResponse,
    CaseExportResponse
)
from app.services.semantic_search_engine import (
    SemanticQueryParser,
    SemanticSearchService,
    InvestigationCaseService
)

router = APIRouter(prefix="/investigation", tags=["Forensic Investigation & Semantic Search"])


# ==========================================
# 1. NATURAL LANGUAGE & SEMANTIC SEARCH
# ==========================================

@router.post("/parse-query", response_model=ParsedSemanticQuery)
async def parse_natural_language_query(
    payload: Dict[str, str],
    db: AsyncSession = Depends(get_db)
):
    """Parses a freeform natural language query into structured filters, entities, attributes, and temporal bounds."""
    query = payload.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    cam_res = await db.execute(select(Camera))
    cams = {c.id: c.name for c in cam_res.scalars().all()}

    return SemanticQueryParser.parse_query(query, available_cameras=cams)


@router.post("/nl-search", response_model=NLSearchResponse)
async def natural_language_semantic_search(
    req: NLSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Executes a full multi-modal natural language search against all real VMS records."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    cam_res = await db.execute(select(Camera))
    cams = {c.id: c.name for c in cam_res.scalars().all()}

    parsed = SemanticQueryParser.parse_query(req.query, available_cameras=cams)
    return await SemanticSearchService.execute_semantic_search(
        parsed_query=parsed,
        min_confidence=req.min_confidence or 0.2,
        limit=req.limit,
        offset=req.offset,
        db=db
    )


# ==========================================
# 2. STRUCTURED FORENSIC SEARCH (POST & GET)
# ==========================================

@router.post("/search", response_model=InvestigationSearchResponse)
async def search_investigation_records_post(
    filters: InvestigationSearchFilter,
    db: AsyncSession = Depends(get_db)
):
    """Unified multi-criteria forensic search endpoint (POST)."""
    return await _execute_unified_search(filters, db)


@router.get("/search", response_model=InvestigationSearchResponse)
async def search_investigation_records_get(
    camera_id: Optional[int] = None,
    object_class: Optional[str] = None,
    track_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    zone_id: Optional[int] = None,
    min_confidence: Optional[float] = None,
    min_dwell_sec: Optional[float] = None,
    color: Optional[str] = None,
    plate_number: Optional[str] = None,
    face_name: Optional[str] = None,
    query_text: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Unified multi-criteria forensic search endpoint (GET)."""
    filter_obj = InvestigationSearchFilter(
        camera_id=camera_id,
        object_class=object_class,
        track_id=track_id,
        event_type=event_type,
        severity=severity,
        zone_id=zone_id,
        min_confidence=min_confidence,
        min_dwell_sec=min_dwell_sec,
        color=color,
        plate_number=plate_number,
        face_name=face_name,
        query_text=query_text,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    return await _execute_unified_search(filter_obj, db)


async def _execute_unified_search(
    filters: InvestigationSearchFilter,
    db: AsyncSession
) -> InvestigationSearchResponse:
    # If query_text, color, or plate_number are provided, map to SemanticSearchService
    raw_q = filters.query_text or ""
    if filters.color:
        raw_q += f" {filters.color}"
    if filters.plate_number:
        raw_q += f" plate {filters.plate_number}"
    if filters.face_name:
        raw_q += f" named {filters.face_name}"

    cam_res = await db.execute(select(Camera))
    cams = {c.id: c.name for c in cam_res.scalars().all()}

    parsed = SemanticQueryParser.parse_query(raw_q, available_cameras=cams)

    if filters.camera_id is not None and filters.camera_id not in parsed.camera_ids:
        parsed.camera_ids.append(filters.camera_id)
    if filters.object_class and filters.object_class not in parsed.object_classes:
        parsed.object_classes.append(filters.object_class)
    if filters.severity and filters.severity not in parsed.severities:
        parsed.severities.append(filters.severity)
    if filters.start_time:
        parsed.time_range_start = filters.start_time
    if filters.end_time:
        parsed.time_range_end = filters.end_time
    if filters.color and filters.color not in parsed.colors:
        parsed.colors.append(filters.color)
    if filters.plate_number and filters.plate_number not in parsed.plate_numbers:
        parsed.plate_numbers.append(filters.plate_number)

    nl_res = await SemanticSearchService.execute_semantic_search(
        parsed_query=parsed,
        min_confidence=filters.min_confidence or 0.2,
        limit=filters.limit,
        offset=filters.offset,
        db=db
    )

    return InvestigationSearchResponse(
        total=nl_res.total,
        limit=nl_res.limit,
        offset=nl_res.offset,
        items=nl_res.items
    )


# ==========================================
# 3. INVESTIGATION CASES & DOSSIERS
# ==========================================

@router.get("/cases", response_model=InvestigationCaseListResponse)
async def list_investigation_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List investigation cases with optional filtering."""
    stmt = select(InvestigationCase)
    conds = []

    if status:
        try:
            conds.append(InvestigationCase.status == CaseStatus(status.upper()))
        except ValueError:
            pass
    if priority:
        try:
            conds.append(InvestigationCase.priority == CasePriority(priority.upper()))
        except ValueError:
            pass
    if search:
        s = f"%{search}%"
        conds.append(
            or_(
                InvestigationCase.case_number.ilike(s),
                InvestigationCase.title.ilike(s),
                InvestigationCase.description.ilike(s),
                InvestigationCase.lead_investigator.ilike(s)
            )
        )

    if conds:
        stmt = stmt.where(and_(*conds))

    stmt = stmt.order_by(desc(InvestigationCase.updated_at))

    # Total count
    count_stmt = select(func.count(InvestigationCase.id))
    if conds:
        count_stmt = count_stmt.where(and_(*conds))
    total = (await db.execute(count_stmt)).scalar() or 0

    res = await db.execute(stmt.limit(limit).offset(offset))
    cases = res.scalars().all()

    items = []
    for c in cases:
        findings_count_res = await db.execute(
            select(func.count(CaseFinding.id)).where(CaseFinding.case_id == c.id)
        )
        f_count = findings_count_res.scalar() or 0
        tags_list = json.loads(c.tags_json) if c.tags_json else []

        items.append(
            InvestigationCaseResponse(
                id=c.id,
                case_number=c.case_number,
                title=c.title,
                description=c.description,
                status=c.status.value if hasattr(c.status, 'value') else str(c.status),
                priority=c.priority.value if hasattr(c.priority, 'value') else str(c.priority),
                lead_investigator=c.lead_investigator,
                hypothesis=c.hypothesis,
                tags=tags_list,
                findings_count=f_count,
                findings=[],
                created_at=c.created_at,
                updated_at=c.updated_at,
                closed_at=c.closed_at
            )
        )

    return InvestigationCaseListResponse(total=total, limit=limit, offset=offset, items=items)


@router.post("/cases", response_model=InvestigationCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation_case(
    payload: InvestigationCaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new investigation case dossier."""
    case = await InvestigationCaseService.create_case(payload.model_dump(), db)
    return InvestigationCaseResponse(
        id=case.id,
        case_number=case.case_number,
        title=case.title,
        description=case.description,
        status=case.status.value if hasattr(case.status, 'value') else str(case.status),
        priority=case.priority.value if hasattr(case.priority, 'value') else str(case.priority),
        lead_investigator=case.lead_investigator,
        hypothesis=case.hypothesis,
        tags=payload.tags,
        findings_count=0,
        findings=[],
        created_at=case.created_at,
        updated_at=case.updated_at,
        closed_at=case.closed_at
    )


@router.get("/cases/{case_id}", response_model=InvestigationCaseResponse)
async def get_investigation_case_detail(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get full investigation case details including all pinned findings."""
    case = await db.get(InvestigationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    findings_res = await db.execute(
        select(CaseFinding).where(CaseFinding.case_id == case_id).order_by(CaseFinding.timestamp.asc(), CaseFinding.created_at.asc())
    )
    findings = findings_res.scalars().all()

    cam_res = await db.execute(select(Camera))
    cams = {c.id: c.name for c in cam_res.scalars().all()}

    finding_responses = [
        CaseFindingResponse(
            id=f.id,
            case_id=f.case_id,
            item_type=f.item_type,
            reference_id=f.reference_id,
            camera_id=f.camera_id,
            camera_name=cams.get(f.camera_id, f"Camera #{f.camera_id}") if f.camera_id else None,
            timestamp=f.timestamp,
            title=f.title,
            notes=f.notes,
            metadata=json.loads(f.metadata_json) if f.metadata_json else {},
            thumbnail_url=f.thumbnail_url,
            created_at=f.created_at
        )
        for f in findings
    ]

    tags_list = json.loads(case.tags_json) if case.tags_json else []

    return InvestigationCaseResponse(
        id=case.id,
        case_number=case.case_number,
        title=case.title,
        description=case.description,
        status=case.status.value if hasattr(case.status, 'value') else str(case.status),
        priority=case.priority.value if hasattr(case.priority, 'value') else str(case.priority),
        lead_investigator=case.lead_investigator,
        hypothesis=case.hypothesis,
        tags=tags_list,
        findings_count=len(findings),
        findings=finding_responses,
        created_at=case.created_at,
        updated_at=case.updated_at,
        closed_at=case.closed_at
    )


@router.put("/cases/{case_id}", response_model=InvestigationCaseResponse)
async def update_investigation_case(
    case_id: int,
    payload: InvestigationCaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update case status, priority, hypothesis, lead investigator, or tags."""
    case = await db.get(InvestigationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    if payload.title is not None:
        case.title = payload.title
    if payload.description is not None:
        case.description = payload.description
    if payload.status is not None:
        try:
            case.status = CaseStatus(payload.status.upper())
            if case.status in [CaseStatus.RESOLVED, CaseStatus.CLOSED] and not case.closed_at:
                case.closed_at = datetime.now(timezone.utc)
            elif case.status in [CaseStatus.OPEN, CaseStatus.UNDER_INVESTIGATION]:
                case.closed_at = None
        except ValueError:
            pass
    if payload.priority is not None:
        try:
            case.priority = CasePriority(payload.priority.upper())
        except ValueError:
            pass
    if payload.lead_investigator is not None:
        case.lead_investigator = payload.lead_investigator
    if payload.hypothesis is not None:
        case.hypothesis = payload.hypothesis
    if payload.tags is not None:
        case.tags_json = json.dumps(payload.tags)

    case.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(case)

    return await get_investigation_case_detail(case_id, db)


@router.delete("/cases/{case_id}")
async def delete_investigation_case(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an investigation case and all associated findings."""
    case = await db.get(InvestigationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    await db.delete(case)
    await db.commit()
    return {"status": "success", "message": f"Case #{case.case_number} deleted"}


# ==========================================
# 4. CASE FINDINGS / PINNED EVIDENCE
# ==========================================

@router.post("/cases/{case_id}/findings", response_model=CaseFindingResponse, status_code=status.HTTP_201_CREATED)
async def add_finding_to_case(
    case_id: int,
    payload: CaseFindingCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add/pin a finding (detection, incident, ANPR, face, evidence, note) to an investigation case."""
    case = await db.get(InvestigationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    finding = CaseFinding(
        case_id=case_id,
        item_type=payload.item_type,
        reference_id=payload.reference_id,
        camera_id=payload.camera_id,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        title=payload.title,
        notes=payload.notes,
        metadata_json=json.dumps(payload.metadata) if payload.metadata else "{}",
        thumbnail_url=payload.thumbnail_url
    )
    db.add(finding)
    case.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(finding)

    cam_name = None
    if finding.camera_id:
        c = await db.get(Camera, finding.camera_id)
        if c:
            cam_name = c.name

    return CaseFindingResponse(
        id=finding.id,
        case_id=finding.case_id,
        item_type=finding.item_type,
        reference_id=finding.reference_id,
        camera_id=finding.camera_id,
        camera_name=cam_name,
        timestamp=finding.timestamp,
        title=finding.title,
        notes=finding.notes,
        metadata=payload.metadata,
        thumbnail_url=finding.thumbnail_url,
        created_at=finding.created_at
    )


@router.delete("/cases/{case_id}/findings/{finding_id}")
async def remove_finding_from_case(
    case_id: int,
    finding_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a finding from an investigation case."""
    finding = await db.get(CaseFinding, finding_id)
    if not finding or finding.case_id != case_id:
        raise HTTPException(status_code=404, detail="Finding not found in this case")

    await db.delete(finding)
    case = await db.get(InvestigationCase, case_id)
    if case:
        case.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "success", "message": f"Finding #{finding_id} removed from Case #{case_id}"}


# ==========================================
# 5. TIMELINE RECONSTRUCTION & DOSSIER EXPORT
# ==========================================

@router.get("/cases/{case_id}/timeline", response_model=CaseTimelineResponse)
async def get_case_timeline(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Reconstructs the chronological multi-camera event timeline and camera sequence for a case."""
    try:
        return await InvestigationCaseService.get_case_timeline(case_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cases/{case_id}/export", response_model=CaseExportResponse)
async def export_case_report(
    case_id: int,
    format: Optional[str] = "json",
    db: AsyncSession = Depends(get_db)
):
    """Exports a comprehensive investigation dossier report (JSON or standalone HTML)."""
    try:
        report = await InvestigationCaseService.export_case_report(case_id, db)
        if format == "html":
            return HTMLResponse(content=report.html_report, status_code=200)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
