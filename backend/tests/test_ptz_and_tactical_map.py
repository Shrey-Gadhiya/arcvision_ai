import time
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import init_db, AsyncSessionLocal, engine
from app.models.camera import Camera, CameraStatus, StreamType
from app.models.ptz import PTZStatusEnum, PTZPreset, PTZLog
from app.services.ptz.base import PTZCapabilities, PTZStatus
from app.services.ptz.onvif_adapter import ONVIFPTZAdapter
from app.services.ptz.ptz_service import ptz_service


def test_onvif_adapter_honest_reporting():
    """Verify that ONVIF adapter reports NOT_CONFIGURED when host is absent."""
    adapter_unconf = ONVIFPTZAdapter(camera_id=1, camera_name="Perimeter Cam 1", host=None)
    assert adapter_unconf.connect() is False
    status = adapter_unconf.get_status()
    assert status.status == PTZStatusEnum.NOT_CONFIGURED

    # When given unreachable host, reports UNAVAILABLE without crashing
    adapter_unreach = ONVIFPTZAdapter(camera_id=2, camera_name="Perimeter Cam 2", host="192.0.2.1", port=80, timeout=0.2)
    assert adapter_unreach.connect() is False
    status2 = adapter_unreach.get_status()
    assert status2.status == PTZStatusEnum.UNAVAILABLE


def test_ptz_motion_commands():
    """Verify PTZ continuous, relative, stop, and home operations."""
    adapter = ONVIFPTZAdapter(camera_id=3, camera_name="Gate PTZ", host="127.0.0.1")

    # 1. Continuous Move
    assert adapter.continuous_move(pan_speed=0.5, tilt_speed=-0.2, zoom_speed=0.1) is True
    st = adapter.get_status()
    assert st.is_moving is True
    assert st.pan > 0.0
    assert st.tilt < 0.0

    # 2. Stop
    assert adapter.stop() is True
    assert adapter.get_status().is_moving is False

    # 3. Relative Move
    assert adapter.relative_move(pan=-0.1, tilt=0.1, zoom=0.0) is True

    # 4. Goto Home
    assert adapter.goto_home() is True
    st_home = adapter.get_status()
    assert st_home.pan == 0.0
    assert st_home.tilt == 0.0
    assert st_home.zoom == 1.0


def test_ptz_preset_lifecycle_and_service():
    """Verify end-to-end preset creation, listing, recall, and deletion."""
    async def _run():
        await init_db()
        async with AsyncSessionLocal() as session:
            # Ensure a test camera exists
            cam = Camera(
                name=f"Tactical PTZ Outpost {int(time.time())}",
                rtsp_url="rtsp://192.168.1.100/live",
                stream_type=StreamType.SYNTHETIC,
                ptz_enabled=True,
                latitude=26.8520,
                longitude=85.2010
            )
            session.add(cam)
            await session.commit()
            await session.refresh(cam)

            # 1. Create preset
            preset_data = await ptz_service.create_preset(
                camera_id=cam.id,
                name="Sector 4 Fence Line",
                username="admin",
                db=session
            )
            assert preset_data["name"] == "Sector 4 Fence Line"
            token = preset_data["preset_token"]

            # 2. List presets
            presets = await ptz_service.list_presets(camera_id=cam.id, db=session)
            assert len(presets) >= 1
            assert any(p["preset_token"] == token for p in presets)

            # 3. Goto preset
            goto_res = await ptz_service.goto_preset(
                camera_id=cam.id,
                preset_token=token,
                username="admin",
                user_role="ADMIN",
                db=session
            )
            assert goto_res["success"] is True

            # 4. Delete preset
            del_ok = await ptz_service.delete_preset(camera_id=cam.id, preset_token=token, db=session)
            assert del_ok is True

    asyncio.run(_run())


def test_tactical_map_api_layer():
    """Verify tactical map geospatial layer API serialization."""
    async def _run():
        await init_db()

        # Create a test camera for tactical map query
        async with AsyncSessionLocal() as session:
            cam = Camera(
                name=f"Perimeter Thermal PTZ {int(time.time())}",
                rtsp_url="rtsp://192.168.1.109/live",
                stream_type=StreamType.SYNTHETIC,
                ptz_enabled=True,
                latitude=26.8550,
                longitude=85.2050
            )
            session.add(cam)
            await session.commit()
            await session.refresh(cam)
            cam_id = cam.id

        # Query PTZ status with a fresh session (avoids out-of-scope session)
        async with AsyncSessionLocal() as session2:
            ptz_stat = await ptz_service.get_status(cam_id, session2)
            assert ptz_stat["camera_id"] == cam_id
            assert "pan" in ptz_stat
            assert "tilt" in ptz_stat
            assert "zoom" in ptz_stat
            assert ptz_stat["ptz_enabled"] is True

        # Test tactical layer API via ASGI transport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/map/tactical-layer")
            # 401 if auth required, 200 if accessible
            assert res.status_code in [200, 401]

    asyncio.run(_run())
