import asyncio
import json
from pathlib import Path
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.camera import Camera, CameraStatus, StreamType
from app.models.zone import Zone, ZoneType, Tripwire, TripwireDirection
from app.services.stream_manager import stream_manager
from app.core.config import settings

async def add_sample():
    sample_path = str(settings.DEMO_DIR / "sample.mp4")
    if not Path(sample_path).exists():
        sample_path = str(settings.BASE_DIR.parent / "sample.mp4")

    async with AsyncSessionLocal() as session:
        # Check if CAM-05 or sample camera already exists
        res = await session.execute(select(Camera).where(Camera.name.like("%Field CCTV%")))
        cam = res.scalars().first()

        if not cam:
            cam = Camera(
                name="CAM-05: Field Perimeter CCTV",
                description="Live multi-person field surveillance feed from user sample.mp4",
                rtsp_url=sample_path,
                stream_type=StreamType.FILE,
                group_name="Field Surveillance",
                location="Sector 4 - Tactical Area Bravo",
                latitude=26.8540,
                longitude=85.2050,
                heading_deg=135.0,
                fov_angle=85.0,
                target_fps=15,
                night_mode_enabled=False
            )
            session.add(cam)
            await session.commit()
            await session.refresh(cam)
            print(f"Created Camera: {cam.name} (ID: {cam.id})")
        else:
            cam.rtsp_url = sample_path
            await session.commit()
            print(f"Updated existing camera: {cam.name} (ID: {cam.id})")

        # Add a restricted zone and virtual fence tripwire for this camera
        z_res = await session.execute(select(Zone).where(Zone.camera_id == cam.id))
        if not z_res.scalars().first():
            z = Zone(
                camera_id=cam.id,
                name="Restricted Movement Zone",
                zone_type=ZoneType.RESTRICTED,
                points_json=json.dumps([
                    {"x": 0.15, "y": 0.35},
                    {"x": 0.85, "y": 0.35},
                    {"x": 0.85, "y": 0.90},
                    {"x": 0.15, "y": 0.90}
                ]),
                color_hex="#EF4444",
                loitering_time_sec=12
            )
            session.add(z)

        tw_res = await session.execute(select(Tripwire).where(Tripwire.camera_id == cam.id))
        if not tw_res.scalars().first():
            tw = Tripwire(
                camera_id=cam.id,
                name="Field Perimeter Fence Line",
                line_json=json.dumps({
                    "start": {"x": 0.1, "y": 0.45},
                    "end": {"x": 0.9, "y": 0.45}
                }),
                direction=TripwireDirection.BIDIRECTIONAL,
                color_hex="#F59E0B"
            )
            session.add(tw)

        await session.commit()

        # Start streamer worker
        streamer = stream_manager.start_streamer(
            camera_id=cam.id,
            camera_name=cam.name,
            stream_url=cam.rtsp_url,
            stream_type="FILE",
            target_fps=15,
            is_night_mode=False
        )
        print(f"Started live stream worker for Camera #{cam.id}")

if __name__ == "__main__":
    asyncio.run(add_sample())
