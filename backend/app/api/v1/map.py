import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import UserRole
from app.models.camera import Camera
from app.models.incident import Incident, IncidentStatus
from app.models.zone import Zone, ZoneType
from app.schemas.all_schemas import CameraGeospatialUpdate
from app.api.v1.auth import get_current_user, require_roles
from app.services.analytics.cross_camera.global_track_manager import global_track_manager
from app.services.analytics.cross_camera.topology_manager import topology_manager

logger = logging.getLogger("arc_vision.api.map")

router = APIRouter(prefix="/map", tags=["Tactical Geospatial Map"])

@router.get("/tactical-layer")
async def get_tactical_map_layer(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Returns unified tactical geospatial surveillance layer:
    - Cameras with FOV cones & orientation
    - Active global tracks with multi-camera journeys
    - Active incidents with threat ratings
    - Camera topology adjacency links
    - Border restricted zones
    """
    # 1. Cameras
    cams_res = await db.execute(select(Camera))
    cameras = cams_res.scalars().all()

    # 2. Active Incidents
    inc_res = await db.execute(
        select(Incident).where(
            Incident.status.in_([IncidentStatus.NEW, IncidentStatus.ACKNOWLEDGED, IncidentStatus.INVESTIGATING])
        )
    )
    active_incidents = inc_res.scalars().all()

    # 3. Restricted Zones
    zones_res = await db.execute(select(Zone).where(Zone.is_active == True))
    all_zones = zones_res.scalars().all()

    # 4. Active Global Tracks
    active_tracks = global_track_manager.list_active_tracks()

    # 5. Topology links
    links = topology_manager.get_all_links()

    camera_features = []
    cam_coord_map = {}
    for c in cameras:
        cam_coord_map[c.id] = {"lat": c.latitude, "lon": c.longitude, "name": c.name}
        camera_features.append({
            "id": c.id,
            "name": c.name,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "altitude_m": c.altitude_m,
            "heading_deg": c.heading_deg,
            "fov_angle": c.fov_angle,
            "range_meters": c.range_meters,
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "location": c.location,
            "group_name": c.group_name,
            "ptz_enabled": c.ptz_enabled,
            "is_night_mode": c.night_mode_enabled
        })

    incident_markers = []
    for inc in active_incidents:
        cam_meta = cam_coord_map.get(inc.camera_id, {"lat": 26.8500, "lon": 85.2000})
        incident_markers.append({
            "id": inc.id,
            "code": inc.incident_code,
            "title": inc.title,
            "severity": inc.severity.value if hasattr(inc.severity, 'value') else str(inc.severity),
            "status": inc.status.value if hasattr(inc.status, 'value') else str(inc.status),
            "threat_score": inc.threat_score,
            "camera_id": inc.camera_id,
            "location_name": inc.location_name,
            "latitude": cam_meta["lat"] + 0.0003, # slight offset for clear visual distinction
            "longitude": cam_meta["lon"] + 0.0003,
            "detected_at": inc.detected_at.isoformat() if inc.detected_at else None
        })

    zone_polygons = []
    for z in all_zones:
        pts = []
        if z.polygon_json:
            try:
                pts = json.loads(z.polygon_json)
            except Exception:
                pass
        zone_polygons.append({
            "id": z.id,
            "camera_id": z.camera_id,
            "name": z.name,
            "zone_type": z.zone_type.value if hasattr(z.zone_type, 'value') else str(z.zone_type),
            "color": z.color,
            "points": pts
        })

    return {
        "sector_name": "Indo-Nepal Border Tactical Sector Alpha (SSB Outpost)",
        "center_lat": 26.8500,
        "center_lon": 85.2000,
        "zoom": 15,
        "cameras": camera_features,
        "active_incidents": incident_markers,
        "global_tracks": active_tracks,
        "topology_links": links,
        "restricted_zones": zone_polygons,
        "timestamp": None
    }

@router.put("/cameras/{camera_id}/geospatial")
async def update_camera_geospatial(
    camera_id: int,
    payload: CameraGeospatialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """
    Updates camera geospatial positioning, FOV cone orientation, and ONVIF/PTZ credentials.
    """
    res = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = res.scalars().first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    if payload.location is not None:
        camera.location = payload.location
    if payload.latitude is not None:
        camera.latitude = payload.latitude
    if payload.longitude is not None:
        camera.longitude = payload.longitude
    if payload.altitude_m is not None:
        camera.altitude_m = payload.altitude_m
    if payload.fov_angle is not None:
        camera.fov_angle = payload.fov_angle
    if payload.heading_deg is not None:
        camera.heading_deg = payload.heading_deg
    if payload.range_meters is not None:
        camera.range_meters = payload.range_meters
    if payload.onvif_host is not None:
        camera.onvif_host = payload.onvif_host
    if payload.onvif_port is not None:
        camera.onvif_port = payload.onvif_port
    if payload.onvif_username is not None:
        camera.onvif_username = payload.onvif_username
    if payload.onvif_password is not None:
        camera.onvif_password_encrypted = payload.onvif_password
    if payload.ptz_enabled is not None:
        camera.ptz_enabled = payload.ptz_enabled

    await db.commit()
    await db.refresh(camera)

    return {
        "success": True,
        "camera_id": camera.id,
        "name": camera.name,
        "latitude": camera.latitude,
        "longitude": camera.longitude,
        "altitude_m": camera.altitude_m,
        "heading_deg": camera.heading_deg,
        "fov_angle": camera.fov_angle,
        "range_meters": camera.range_meters,
        "ptz_enabled": camera.ptz_enabled,
        "onvif_host": camera.onvif_host
    }
