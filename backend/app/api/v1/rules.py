import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.rule import Rule
from app.models.user import UserRole
from app.models.audit import AuditLog, AuditAction
from app.schemas.all_schemas import RuleResponse, RuleCreate, RuleUpdate
from app.services.stream_manager import stream_manager
from app.api.v1.auth import get_current_user, require_roles

router = APIRouter(prefix="/rules", tags=["Rules Engine"])

async def sync_all_rules(db: AsyncSession):
    result = await db.execute(select(Rule).where(Rule.is_active == True))
    active_rules = result.scalars().all()
    for streamer in stream_manager.get_all_streamers().values():
        streamer.update_config(rules=active_rules)

@router.get("/", response_model=List[RuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lists all intelligent behavior rules."""
    result = await db.execute(select(Rule).order_by(Rule.id))
    return result.scalars().all()

@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fetches details for a single behavior rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """Creates a new behavioral rule."""
    rule = Rule(**data.model_dump())
    db.add(rule)
    await db.flush()

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.CREATE,
        resource_type="BEHAVIOR_RULE",
        resource_id=str(rule.id),
        details_json=json.dumps({"description": f"Created behavior rule '{rule.name}' ({rule.event_type.value})"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(rule)
    await sync_all_rules(db)
    return rule

@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """Updates an existing behavior rule configuration."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(rule, key, value)

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.UPDATE,
        resource_type="BEHAVIOR_RULE",
        resource_id=str(rule.id),
        details_json=json.dumps({"description": f"Updated rule '{rule.name}' parameters: {list(update_dict.keys())}"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(rule)
    await sync_all_rules(db)
    return rule

@router.put("/{rule_id}/toggle", response_model=RuleResponse)
async def toggle_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """Toggles rule active/inactive state."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = not rule.is_active

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.UPDATE,
        resource_type="BEHAVIOR_RULE",
        resource_id=str(rule.id),
        details_json=json.dumps({"description": f"Toggled rule '{rule.name}' active state to {rule.is_active}"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(rule)
    await sync_all_rules(db)
    return rule

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """Deletes a behavior rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule_name = rule.name
    await db.delete(rule)

    audit = AuditLog(
        username=current_user.username,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action=AuditAction.DELETE,
        resource_type="BEHAVIOR_RULE",
        resource_id=str(rule_id),
        details_json=json.dumps({"description": f"Deleted behavior rule '{rule_name}' (ID #{rule_id})"}),
        ip_address="127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await sync_all_rules(db)
    return None
