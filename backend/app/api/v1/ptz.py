import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import UserRole
from app.models.camera import Camera
from app.schemas.all_schemas import (
    PTZMoveRequest,
    PTZRelativeMoveRequest,
    PTZPresetCreate,
    PTZPresetResponse,
    PTZStatusResponse,
    PTZCapabilitiesResponse
)
from app.api.v1.auth import get_current_user, require_roles
from app.services.ptz.ptz_service import ptz_service

logger = logging.getLogger("arc_vision.api.ptz")

router = APIRouter(prefix="/ptz", tags=["ONVIF & PTZ Camera Control"])

@router.get("/{camera_id}/status", response_model=PTZStatusResponse)
async def get_ptz_status(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Returns current PTZ status, operational capability, and hardware connection state.
    """
    status_dict = await ptz_service.get_status(camera_id, db)
    return PTZStatusResponse(**status_dict)

@router.get("/{camera_id}/capabilities", response_model=PTZCapabilitiesResponse)
async def get_ptz_capabilities(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Returns supported PTZ capabilities (pan, tilt, zoom, presets, home, speed control).
    """
    caps_dict = await ptz_service.get_capabilities(camera_id, db)
    return PTZCapabilitiesResponse(**caps_dict)

@router.post("/{camera_id}/move")
async def continuous_move(
    camera_id: int,
    payload: PTZMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """
    Executes continuous pan/tilt/zoom movement vector.
    """
    role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    res = await ptz_service.continuous_move(
        camera_id=camera_id,
        pan_speed=payload.pan_speed,
        tilt_speed=payload.tilt_speed,
        zoom_speed=payload.zoom_speed,
        speed=payload.speed,
        username=current_user.username,
        user_role=role_str,
        db=db
    )
    return res

@router.post("/{camera_id}/relative-move")
async def relative_move(
    camera_id: int,
    payload: PTZRelativeMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """
    Executes relative pan/tilt/zoom offset step.
    """
    role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    res = await ptz_service.relative_move(
        camera_id=camera_id,
        pan=payload.pan,
        tilt=payload.tilt,
        zoom=payload.zoom,
        speed=payload.speed,
        username=current_user.username,
        user_role=role_str,
        db=db
    )
    return res

@router.post("/{camera_id}/stop")
async def stop_ptz_movement(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """
    Stops all active PTZ pan/tilt/zoom motion.
    """
    role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    res = await ptz_service.stop(
        camera_id=camera_id,
        username=current_user.username,
        user_role=role_str,
        db=db
    )
    return res

@router.post("/{camera_id}/home")
async def goto_home_position(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """
    Recalls default home position.
    """
    role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    res = await ptz_service.goto_home(
        camera_id=camera_id,
        username=current_user.username,
        user_role=role_str,
        db=db
    )
    return res

@router.get("/{camera_id}/presets", response_model=List[PTZPresetResponse])
async def list_ptz_presets(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lists saved PTZ presets for a camera.
    """
    presets = await ptz_service.list_presets(camera_id, db)
    return [PTZPresetResponse(**p) for p in presets]

@router.post("/{camera_id}/presets", response_model=PTZPresetResponse)
async def create_ptz_preset(
    camera_id: int,
    payload: PTZPresetCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """
    Saves current camera pan/tilt/zoom position as a named preset.
    """
    preset = await ptz_service.create_preset(
        camera_id=camera_id,
        name=payload.name,
        username=current_user.username,
        db=db
    )
    return PTZPresetResponse(**preset)

@router.post("/{camera_id}/presets/{preset_token}/goto")
async def goto_ptz_preset(
    camera_id: int,
    preset_token: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER, UserRole.OPERATOR]))
):
    """
    Commands camera to move to a saved preset position.
    """
    role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    res = await ptz_service.goto_preset(
        camera_id=camera_id,
        preset_token=preset_token,
        username=current_user.username,
        user_role=role_str,
        db=db
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res.get("error", "Preset not found"))
    return res

@router.delete("/{camera_id}/presets/{preset_token}")
async def delete_ptz_preset(
    camera_id: int,
    preset_token: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """
    Deletes a saved PTZ preset.
    """
    ok = await ptz_service.delete_preset(camera_id, preset_token, db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    return {"success": True, "message": f"Preset {preset_token} deleted"}

@router.post("/{camera_id}/test")
async def test_onvif_connection(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """
    Tests ONVIF connectivity and returns honest diagnostic status.
    """
    res = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = res.scalars().first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    adapter = ptz_service.get_or_create_adapter(camera)
    is_connected = adapter.connect()
    status_obj = adapter.get_status()

    return {
        "camera_id": camera_id,
        "camera_name": camera.name,
        "onvif_host": camera.onvif_host,
        "onvif_port": camera.onvif_port,
        "is_connected": is_connected,
        "status": status_obj.status.value,
        "error_message": status_obj.error_message
    }
