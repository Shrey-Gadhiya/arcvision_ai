import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.zone import Zone, Tripwire, ZoneType, TripwireDirection
from app.schemas.all_schemas import ZoneResponse, ZoneCreate, TripwireResponse, TripwireCreate
from app.services.stream_manager import stream_manager
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/zones", tags=["Zones & Tripwires"])

def sync_camera_zones(camera_id: int, zones_list: List[Zone], tripwires_list: List[Tripwire]):
    streamer = stream_manager.get_streamer(camera_id)
    if not streamer:
        return

    parsed_zones = []
    for z in zones_list:
        if z.is_active:
            try:
                pts = json.loads(z.points_json)
                parsed_zones.append({
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type.value,
                    "points": [(p["x"], p["y"]) for p in pts],
                    "loitering_time_sec": z.loitering_time_sec
                })
            except Exception:
                pass

    parsed_tripwires = []
    for tw in tripwires_list:
        if tw.is_active:
            try:
                line_data = json.loads(tw.line_json)
                parsed_tripwires.append({
                    "id": tw.id,
                    "name": tw.name,
                    "direction": tw.direction.value,
                    "line": {
                        "start": (line_data["start"]["x"], line_data["start"]["y"]),
                        "end": (line_data["end"]["x"], line_data["end"]["y"])
                    }
                })
            except Exception:
                pass

    streamer.update_config(zones=parsed_zones, tripwires=parsed_tripwires)

# --- ZONES ---
@router.get("/camera/{camera_id}", response_model=List[ZoneResponse])
async def get_camera_zones(camera_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zone).where(Zone.camera_id == camera_id))
    return result.scalars().all()

@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(data: ZoneCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    zone = Zone(**data.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)

    # Sync with streamer
    z_res = await db.execute(select(Zone).where(Zone.camera_id == zone.camera_id))
    tw_res = await db.execute(select(Tripwire).where(Tripwire.camera_id == zone.camera_id))
    sync_camera_zones(zone.camera_id, z_res.scalars().all(), tw_res.scalars().all())

    return zone

@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = result.scalars().first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    cam_id = zone.camera_id
    await db.delete(zone)
    await db.commit()

    z_res = await db.execute(select(Zone).where(Zone.camera_id == cam_id))
    tw_res = await db.execute(select(Tripwire).where(Tripwire.camera_id == cam_id))
    sync_camera_zones(cam_id, z_res.scalars().all(), tw_res.scalars().all())
    return None

# --- TRIPWIRES ---
@router.get("/tripwires/camera/{camera_id}", response_model=List[TripwireResponse])
async def get_camera_tripwires(camera_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tripwire).where(Tripwire.camera_id == camera_id))
    return result.scalars().all()

@router.post("/tripwires", response_model=TripwireResponse, status_code=status.HTTP_201_CREATED)
async def create_tripwire(data: TripwireCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    tw = Tripwire(**data.model_dump())
    db.add(tw)
    await db.commit()
    await db.refresh(tw)

    z_res = await db.execute(select(Zone).where(Zone.camera_id == tw.camera_id))
    tw_res = await db.execute(select(Tripwire).where(Tripwire.camera_id == tw.camera_id))
    sync_camera_zones(tw.camera_id, z_res.scalars().all(), tw_res.scalars().all())

    return tw

@router.delete("/tripwires/{tripwire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tripwire(tripwire_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    result = await db.execute(select(Tripwire).where(Tripwire.id == tripwire_id))
    tw = result.scalars().first()
    if not tw:
        raise HTTPException(status_code=404, detail="Tripwire not found")
    
    cam_id = tw.camera_id
    await db.delete(tw)
    await db.commit()

    z_res = await db.execute(select(Zone).where(Zone.camera_id == cam_id))
    tw_res = await db.execute(select(Tripwire).where(Tripwire.camera_id == cam_id))
    sync_camera_zones(cam_id, z_res.scalars().all(), tw_res.scalars().all())
    return None
