import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.event_bus import event_bus
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.models.evidence import Evidence
from app.models.event import DetectionEvent, RuleEvent
from app.models.audit import AuditLog
from app.schemas.all_schemas import (
    IncidentResponse,
    IncidentStatusUpdate,
    IncidentTransitionRequest,
    IncidentAssignRequest,
    IncidentAddNote,
    EvidenceResponse
)
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/incidents", tags=["Incidents & Threat Lifecycle"])

VALID_TRANSITIONS: Dict[IncidentStatus, List[IncidentStatus]] = {
    IncidentStatus.DETECTED: [IncidentStatus.TRIAGED, IncidentStatus.ACKNOWLEDGED, IncidentStatus.CLOSED],
    IncidentStatus.TRIAGED: [IncidentStatus.ACKNOWLEDGED, IncidentStatus.INVESTIGATING, IncidentStatus.CLOSED],
    IncidentStatus.ACKNOWLEDGED: [IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED, IncidentStatus.CLOSED],
    IncidentStatus.INVESTIGATING: [IncidentStatus.RESOLVED, IncidentStatus.CLOSED],
    IncidentStatus.RESOLVED: [IncidentStatus.CLOSED, IncidentStatus.INVESTIGATING],
    IncidentStatus.CLOSED: [IncidentStatus.INVESTIGATING] # Re-open
}

@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
    camera_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = select(Incident).order_by(desc(Incident.detected_at))
    if status:
        query = query.where(Incident.status == status)
    if severity:
        query = query.where(Incident.severity == severity)
    if camera_id:
        query = query.where(Incident.camera_id == camera_id)

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = result.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc

@router.post("/{incident_id}/transition", response_model=IncidentResponse)
async def transition_incident_status(
    incident_id: int,
    data: IncidentTransitionRequest,
    user: str = "operator",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = result.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    current_status = inc.status
    target_status = data.target_status

    # Validate transition
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed and target_status != current_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid incident state transition from '{current_status.value}' to '{target_status.value}'. Allowed transitions: {[s.value for s in allowed]}"
        )

    now = datetime.now(timezone.utc)
    inc.status = target_status

    # Update lifecycle timestamp & actor fields
    if target_status == IncidentStatus.TRIAGED:
        inc.triaged_at = now
        inc.triaged_by = user
    elif target_status == IncidentStatus.ACKNOWLEDGED:
        inc.acknowledged_at = now
        inc.acknowledged_by = user
    elif target_status == IncidentStatus.RESOLVED:
        inc.resolved_at = now
        inc.resolved_by = user
        if data.reason:
            inc.resolution_reason = data.reason
        if data.note:
            inc.resolution_notes = data.note
    elif target_status == IncidentStatus.CLOSED:
        inc.closed_at = now
        inc.closed_by = user
        if data.reason:
            inc.resolution_reason = data.reason
        if data.note:
            inc.resolution_notes = data.note

    # Record transition history
    history = json.loads(inc.transition_history_json) if inc.transition_history_json else []
    history.append({
        "from_status": current_status.value,
        "to_status": target_status.value,
        "user": user,
        "reason": data.reason or "",
        "note": data.note or "",
        "timestamp": now.isoformat()
    })
    inc.transition_history_json = json.dumps(history)

    # Optional operator note
    if data.note:
        notes = json.loads(inc.operator_notes_json) if inc.operator_notes_json else []
        notes.append({
            "timestamp": now.isoformat(),
            "user": user,
            "text": f"Status changed to {target_status.value}: {data.note}"
        })
        inc.operator_notes_json = json.dumps(notes)

    # Audit log
    audit = AuditLog(
        username=user,
        user_role="OPERATOR",
        action=f"INCIDENT_TRANSITION_{target_status.value}",
        resource_type="INCIDENT",
        resource_id=str(inc.id),
        details_json=json.dumps({"from": current_status.value, "to": target_status.value, "reason": data.reason})
    )
    db.add(audit)
    await db.commit()
    await db.refresh(inc)

    # Broadcast event
    await event_bus.publish("incident:status_changed", {
        "incident_id": inc.id,
        "incident_code": inc.incident_code,
        "status": inc.status.value,
        "updated_by": user
    })

    return inc

@router.post("/{incident_id}/status", response_model=IncidentResponse)
async def update_incident_status(
    incident_id: int,
    data: IncidentStatusUpdate,
    user: str = "operator",
    db: AsyncSession = Depends(get_db)
):
    # Route through standard transition logic
    trans_req = IncidentTransitionRequest(
        target_status=data.status,
        reason=data.resolution_reason,
        note=data.note or data.resolution_notes
    )
    return await transition_incident_status(incident_id=incident_id, data=trans_req, user=user, db=db)

@router.post("/{incident_id}/assign", response_model=IncidentResponse)
async def assign_incident(
    incident_id: int,
    data: IncidentAssignRequest,
    assigned_by: str = "commander",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = result.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    now = datetime.now(timezone.utc)
    inc.assigned_to = data.assigned_to
    inc.assigned_at = now

    notes = json.loads(inc.operator_notes_json) if inc.operator_notes_json else []
    notes.append({
        "timestamp": now.isoformat(),
        "user": assigned_by,
        "text": f"Incident assigned to {data.assigned_to}. {data.note or ''}".strip()
    })
    inc.operator_notes_json = json.dumps(notes)

    await db.commit()
    await db.refresh(inc)
    return inc

@router.post("/{incident_id}/notes", response_model=IncidentResponse)
async def add_incident_note(
    incident_id: int,
    data: IncidentAddNote,
    user: str = "operator",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = result.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    now = datetime.now(timezone.utc)
    notes = json.loads(inc.operator_notes_json) if inc.operator_notes_json else []
    notes.append({
        "timestamp": now.isoformat(),
        "user": user,
        "text": data.note
    })
    inc.operator_notes_json = json.dumps(notes)

    await db.commit()
    await db.refresh(inc)
    return inc

@router.get("/{incident_id}/evidence", response_model=List[EvidenceResponse])
async def get_incident_evidence(incident_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Evidence).where(Evidence.incident_id == incident_id))
    return result.scalars().all()
