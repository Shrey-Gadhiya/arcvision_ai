from fastapi import APIRouter
from app.services.stream_manager import stream_manager

router = APIRouter(tags=["System Health"])

@router.get("/health")
@router.get("/health/")
@router.get("/system/health")
@router.get("/system/health/")
async def get_health():
    return stream_manager.get_system_health()
