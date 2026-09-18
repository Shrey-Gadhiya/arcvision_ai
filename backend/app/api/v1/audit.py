from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.audit import AuditLog
from app.schemas.all_schemas import AuditLogResponse
from app.api.v1.auth import get_current_user, require_roles
from app.models.user import UserRole

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.AUDITOR]))
):
    result = await db.execute(select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit))
    return result.scalars().all()
