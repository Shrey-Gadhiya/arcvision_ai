import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import mask_secret
from app.models.integration import IntegrationConfig, IntegrationType, IntegrationStatus
from app.schemas.all_schemas import (
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    IntegrationConfigResponse
)

router = APIRouter(prefix="/integrations", tags=["Integrations & C2"])

@router.get("/", response_model=List[IntegrationConfigResponse])
async def list_integrations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntegrationConfig).order_by(IntegrationConfig.id))
    configs = result.scalars().all()
    # Attach masked secret
    res = []
    for c in configs:
        item = IntegrationConfigResponse.model_validate(c)
        item.masked_secret = mask_secret(c.auth_secret)
        res.append(item)
    return res

@router.post("/", response_model=IntegrationConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(data: IntegrationConfigCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(IntegrationConfig).where(IntegrationConfig.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Integration with name '{data.name}' already exists.")

    cfg = IntegrationConfig(**data.model_dump())
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    res = IntegrationConfigResponse.model_validate(cfg)
    res.masked_secret = mask_secret(cfg.auth_secret)
    return res

@router.put("/{intg_id}", response_model=IntegrationConfigResponse)
async def update_integration(intg_id: int, data: IntegrationConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntegrationConfig).where(IntegrationConfig.id == intg_id))
    cfg = result.scalars().first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cfg, k, v)

    await db.commit()
    await db.refresh(cfg)
    res = IntegrationConfigResponse.model_validate(cfg)
    res.masked_secret = mask_secret(cfg.auth_secret)
    return res

@router.delete("/{intg_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(intg_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntegrationConfig).where(IntegrationConfig.id == intg_id))
    cfg = result.scalars().first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(cfg)
    await db.commit()
    return None
