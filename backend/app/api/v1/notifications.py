import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.notification import Notification, NotificationRule, NotificationChannel
from app.schemas.all_schemas import (
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
    NotificationResponse
)

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])

@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).order_by(Notification.id.desc()).limit(limit))
    return result.scalars().all()

@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.is_read == False))
    notifs = result.scalars().all()
    for n in notifs:
        n.is_read = True
    await db.commit()
    return {"status": "SUCCESS", "updated_count": len(notifs)}

@router.get("/rules", response_model=List[NotificationRuleResponse])
async def list_notification_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationRule).order_by(NotificationRule.id))
    return result.scalars().all()

@router.post("/rules", response_model=NotificationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_rule(data: NotificationRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = NotificationRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationRule).where(NotificationRule.id == rule_id))
    r = result.scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    await db.delete(r)
    await db.commit()
    return None
