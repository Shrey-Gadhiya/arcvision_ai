import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.camera import Camera
from app.models.ptz import PTZPreset, PTZLog, PTZStatusEnum
from app.models.audit import AuditLog, AuditAction
from app.services.ptz.base import BasePTZAdapter, PTZCapabilities, PTZStatus
from app.services.ptz.onvif_adapter import ONVIFPTZAdapter

logger = logging.getLogger("arc_vision.ptz.service")

class PTZService:
    """
    Central PTZ Controller and Hardware Management Service.
    """
    def __init__(self):
        # In-memory adapter cache: camera_id -> BasePTZAdapter
        self._adapters: Dict[int, BasePTZAdapter] = {}

    def get_or_create_adapter(self, camera: Camera) -> BasePTZAdapter:
        if camera.id not in self._adapters:
            adapter = ONVIFPTZAdapter(
                camera_id=camera.id,
                camera_name=camera.name,
                host=camera.onvif_host,
                port=camera.onvif_port or 80,
                username=camera.onvif_username,
                password=camera.onvif_password_encrypted,
                profile_token=camera.onvif_profile_token
            )
            self._adapters[camera.id] = adapter
        return self._adapters[camera.id]

    async def get_status(self, camera_id: int, db: AsyncSession) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            return {
                "camera_id": camera_id,
                "status": PTZStatusEnum.NOT_CONFIGURED.value,
                "is_moving": False,
                "pan": 0.0,
                "tilt": 0.0,
                "zoom": 1.0,
                "error_message": "Camera not found"
            }

        adapter = self.get_or_create_adapter(camera)
        status_obj = adapter.get_status()
        return {
            "camera_id": camera_id,
            "camera_name": camera.name,
            "ptz_enabled": camera.ptz_enabled,
            "onvif_host": camera.onvif_host or "NOT_CONFIGURED",
            "onvif_port": camera.onvif_port or 80,
            **status_obj.to_dict()
        }

    async def get_capabilities(self, camera_id: int, db: AsyncSession) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            return PTZCapabilities().to_dict()

        adapter = self.get_or_create_adapter(camera)
        caps = adapter.get_capabilities()
        return caps.to_dict()

    async def continuous_move(
        self,
        camera_id: int,
        pan_speed: float,
        tilt_speed: float,
        zoom_speed: float,
        speed: float,
        username: str,
        user_role: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            return {"success": False, "error": "Camera not found"}

        adapter = self.get_or_create_adapter(camera)
        ok = adapter.continuous_move(
            pan_speed=pan_speed * speed,
            tilt_speed=tilt_speed * speed,
            zoom_speed=zoom_speed * speed
        )

        # Log action in PTZLog & AuditLog
        params = {"pan_speed": pan_speed, "tilt_speed": tilt_speed, "zoom_speed": zoom_speed, "speed": speed}
        ptz_log = PTZLog(
            camera_id=camera_id,
            username=username,
            action="CONTINUOUS_MOVE",
            parameters_json=json.dumps(params),
            status=PTZStatusEnum.CONNECTED if ok else PTZStatusEnum.ERROR
        )
        db.add(ptz_log)

        audit = AuditLog(
            username=username,
            user_role=user_role,
            action=AuditAction.UPDATE,
            resource_type="PTZ_CONTROL",
            resource_id=f"cam_{camera_id}",
            details=f"PTZ ContinuousMove executed on Cam #{camera_id} ({camera.name}) by {username}",
            ip_address="127.0.0.1",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        await db.commit()

        return {
            "success": ok,
            "camera_id": camera_id,
            "status": adapter.get_status().to_dict()
        }

    async def relative_move(
        self,
        camera_id: int,
        pan: float,
        tilt: float,
        zoom: float,
        speed: float,
        username: str,
        user_role: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            return {"success": False, "error": "Camera not found"}

        adapter = self.get_or_create_adapter(camera)
        ok = adapter.relative_move(pan=pan, tilt=tilt, zoom=zoom, speed=speed)

        params = {"pan": pan, "tilt": tilt, "zoom": zoom, "speed": speed}
        db.add(PTZLog(
            camera_id=camera_id,
            username=username,
            action="RELATIVE_MOVE",
            parameters_json=json.dumps(params),
            status=PTZStatusEnum.CONNECTED if ok else PTZStatusEnum.ERROR
        ))
        await db.commit()

        return {
            "success": ok,
            "camera_id": camera_id,
            "status": adapter.get_status().to_dict()
        }

    async def stop(
        self,
        camera_id: int,
        username: str,
        user_role: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            return {"success": False, "error": "Camera not found"}

        adapter = self.get_or_create_adapter(camera)
        ok = adapter.stop()

        db.add(PTZLog(
            camera_id=camera_id,
            username=username,
            action="STOP",
            parameters_json="{}",
            status=PTZStatusEnum.CONNECTED
        ))
        await db.commit()

        return {
            "success": ok,
            "camera_id": camera_id,
            "status": adapter.get_status().to_dict()
        }

    async def goto_home(
        self,
        camera_id: int,
        username: str,
        user_role: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            return {"success": False, "error": "Camera not found"}

        adapter = self.get_or_create_adapter(camera)
        ok = adapter.goto_home()

        db.add(PTZLog(
            camera_id=camera_id,
            username=username,
            action="HOME",
            parameters_json="{}",
            status=PTZStatusEnum.CONNECTED
        ))
        await db.commit()

        return {
            "success": ok,
            "camera_id": camera_id,
            "status": adapter.get_status().to_dict()
        }

    async def list_presets(self, camera_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        res = await db.execute(
            select(PTZPreset).where(PTZPreset.camera_id == camera_id).order_by(PTZPreset.id)
        )
        presets = res.scalars().all()
        return [
            {
                "id": p.id,
                "camera_id": p.camera_id,
                "preset_token": p.preset_token,
                "name": p.name,
                "pan": p.pan,
                "tilt": p.tilt,
                "zoom": p.zoom,
                "is_home": p.is_home,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in presets
        ]

    async def create_preset(
        self,
        camera_id: int,
        name: str,
        username: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = res.scalars().first()
        if not camera:
            raise ValueError(f"Camera {camera_id} not found")

        adapter = self.get_or_create_adapter(camera)
        status_obj = adapter.get_status()

        token = f"preset_{int(time.time())}"
        preset = PTZPreset(
            camera_id=camera_id,
            preset_token=token,
            name=name,
            pan=status_obj.pan,
            tilt=status_obj.tilt,
            zoom=status_obj.zoom,
            is_home=False
        )
        db.add(preset)
        await db.commit()
        await db.refresh(preset)

        return {
            "id": preset.id,
            "camera_id": preset.camera_id,
            "preset_token": preset.preset_token,
            "name": preset.name,
            "pan": preset.pan,
            "tilt": preset.tilt,
            "zoom": preset.zoom,
            "is_home": preset.is_home,
            "created_at": preset.created_at.isoformat()
        }

    async def goto_preset(
        self,
        camera_id: int,
        preset_token: str,
        username: str,
        user_role: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(PTZPreset).where(PTZPreset.camera_id == camera_id, PTZPreset.preset_token == preset_token)
        )
        preset = res.scalars().first()
        if not preset:
            return {"success": False, "error": f"Preset {preset_token} not found"}

        cam_res = await db.execute(select(Camera).where(Camera.id == camera_id))
        camera = cam_res.scalars().first()
        if not camera:
            return {"success": False, "error": "Camera not found"}

        adapter = self.get_or_create_adapter(camera)
        ok = adapter.absolute_move(pan=preset.pan, tilt=preset.tilt, zoom=preset.zoom)

        db.add(PTZLog(
            camera_id=camera_id,
            username=username,
            action=f"GOTO_PRESET_{preset.name}",
            parameters_json=json.dumps({"preset_token": preset_token, "name": preset.name}),
            status=PTZStatusEnum.CONNECTED
        ))
        await db.commit()

        return {
            "success": ok,
            "camera_id": camera_id,
            "preset_name": preset.name,
            "status": adapter.get_status().to_dict()
        }

    async def delete_preset(self, camera_id: int, preset_token: str, db: AsyncSession) -> bool:
        res = await db.execute(
            select(PTZPreset).where(PTZPreset.camera_id == camera_id, PTZPreset.preset_token == preset_token)
        )
        preset = res.scalars().first()
        if not preset:
            return False

        await db.delete(preset)
        await db.commit()
        return True

ptz_service = PTZService()
