import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import UserRole
from app.models.cross_camera import (
    GlobalTrack,
    TrackObservation,
    CameraTopology,
    GlobalEntityType,
    IdentitySource
)
from app.models.audit import AuditLog, AuditAction
from app.schemas.all_schemas import (
    GlobalTrackResponse,
    GlobalTrackDetailResponse,
    TrackObservationResponse,
    CameraTopologyCreate,
    CameraTopologyResponse,
    CrossCameraSearchRequest
)
from app.api.v1.auth import get_current_user, require_roles
from app.services.analytics.cross_camera.global_track_manager import global_track_manager
from app.services.analytics.cross_camera.topology_manager import topology_manager

logger = logging.getLogger("arc_vision.api.cross_camera")

router = APIRouter(prefix="/cross-camera", tags=["Cross-Camera Intelligence & Re-ID"])

@router.get("/status")
async def get_cross_camera_status():
    """
    Returns the operational status of all cross-camera correlation subsystems.
    Explicitly reports whether ReID deep models are active or in STANDBY.
    """
    person_reid = global_track_manager.person_reid_adapter.get_status()
    vehicle_reid = global_track_manager.vehicle_reid_adapter.get_status()
    
    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "plate_correlation": {
                "status": "OPERATIONAL",
                "mode": "EXPLICIT_ALPR_MATCH",
                "description": "Deterministic multi-camera vehicle tracking via verified license plates."
            },
            "face_correlation": {
                "status": "OPERATIONAL",
                "mode": "BIOMETRIC_IDENTITY_MATCH",
                "description": "Multi-camera person tracking via verified facial biometric identities."
            },
            "topology_graph": {
                "status": "OPERATIONAL",
                "links_count": len(topology_manager.get_all_links()),
                "description": "Spatial-temporal travel time validation and camera adjacency constraints."
            },
            "appearance_person_reid": {
                "status": person_reid["status"],
                "model_name": person_reid["model_name"],
                "provider": person_reid["provider"],
                "reason": "Deep appearance embedding model not loaded. Operating in metadata & biometric correlation mode."
            },
            "appearance_vehicle_reid": {
                "status": vehicle_reid["status"],
                "model_name": vehicle_reid["model_name"],
                "provider": vehicle_reid["provider"],
                "reason": "Deep vehicle visual feature model not loaded. Operating in ALPR correlation mode."
            }
        },
        "active_global_tracks_count": len(global_track_manager._active_tracks)
    }

@router.get("/tracks", response_model=List[GlobalTrackResponse])
async def list_global_tracks(
    entity_type: Optional[str] = None,
    plate_number: Optional[str] = None,
    face_identity_name: Optional[str] = None,
    current_sector: Optional[str] = None,
    current_camera_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Retrieves global tracks with filtering and pagination.
    """
    query = select(GlobalTrack).order_by(desc(GlobalTrack.last_seen))

    if entity_type:
        try:
            e_enum = GlobalEntityType(entity_type.upper())
            query = query.where(GlobalTrack.entity_type == e_enum)
        except ValueError:
            pass

    if plate_number:
        query = query.where(GlobalTrack.plate_number.ilike(f"%{plate_number}%"))

    if face_identity_name:
        query = query.where(GlobalTrack.face_identity_name.ilike(f"%{face_identity_name}%"))

    if current_sector:
        query = query.where(GlobalTrack.current_sector.ilike(f"%{current_sector}%"))

    if current_camera_id is not None:
        query = query.where(GlobalTrack.current_camera_id == current_camera_id)

    if is_active is not None:
        query = query.where(GlobalTrack.is_active == is_active)

    query = query.offset(offset).limit(limit)
    res = await db.execute(query)
    tracks = res.scalars().all()

    # Log audit entry for entity investigation access
    if plate_number or face_identity_name:
        audit = AuditLog(
            username=current_user.username,
            user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
            action=AuditAction.VIEW,
            resource_type="GLOBAL_TRACK_SEARCH",
            resource_id=f"query_p_{plate_number}_f_{face_identity_name}",
            details=f"User {current_user.username} queried global tracks with filter: plate={plate_number}, face={face_identity_name}",
            ip_address="127.0.0.1",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        await db.commit()

    return [
        GlobalTrackResponse(
            id=t.id,
            global_id=t.global_id,
            entity_type=t.entity_type.value if hasattr(t.entity_type, 'value') else str(t.entity_type),
            current_camera_id=t.current_camera_id,
            current_sector=t.current_sector,
            plate_number=t.plate_number,
            face_identity_id=t.face_identity_id,
            face_identity_name=t.face_identity_name,
            confidence=t.confidence,
            identity_source=t.identity_source.value if hasattr(t.identity_source, 'value') else str(t.identity_source),
            first_seen=t.first_seen,
            last_seen=t.last_seen,
            is_active=t.is_active,
            total_observations=0
        )
        for t in tracks
    ]

@router.get("/tracks/{global_id}", response_model=GlobalTrackDetailResponse)
async def get_global_track_detail(
    global_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Returns comprehensive journey, sightings, and observation history for a specific global entity.
    """
    res = await db.execute(
        select(GlobalTrack)
        .options(selectinload(GlobalTrack.observations))
        .where(GlobalTrack.global_id == global_id)
    )
    track = res.scalars().first()

    if not track:
        # Check in-memory if not persisted
        mem_track = global_track_manager._active_tracks.get(global_id)
        if not mem_track:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Global track {global_id} not found")
        
        return GlobalTrackDetailResponse(
            id=mem_track.id,
            global_id=mem_track.global_id,
            entity_type=mem_track.entity_type.value,
            current_camera_id=mem_track.current_camera_id,
            current_sector=mem_track.current_sector,
            plate_number=mem_track.plate_number,
            face_identity_id=mem_track.face_identity_id,
            face_identity_name=mem_track.face_identity_name,
            confidence=mem_track.confidence,
            identity_source=mem_track.identity_source.value,
            first_seen=datetime.fromtimestamp(mem_track.first_seen, tz=timezone.utc),
            last_seen=datetime.fromtimestamp(mem_track.last_seen, tz=timezone.utc),
            is_active=True,
            total_observations=len(mem_track.camera_hops),
            observations=[],
            journey_hops=mem_track.camera_hops
        )

    # Format observations
    obs_list = []
    journey_hops = []
    for obs in sorted(track.observations, key=lambda x: x.timestamp):
        zones = []
        if obs.zones_json:
            try:
                zones = json.loads(obs.zones_json)
            except Exception:
                pass

        obs_list.append(TrackObservationResponse(
            id=obs.id,
            global_track_id=obs.global_track_id,
            camera_id=obs.camera_id,
            local_track_id=obs.local_track_id,
            camera_name=obs.camera_name,
            sector_name=obs.sector_name,
            duration_sec=obs.duration_sec,
            timestamp=obs.timestamp,
            zones=zones
        ))

        journey_hops.append({
            "camera_id": obs.camera_id,
            "camera_name": obs.camera_name,
            "sector": obs.sector_name,
            "timestamp": obs.timestamp.strftime("%H:%M:%S") if obs.timestamp else "",
            "zones": zones
        })

    return GlobalTrackDetailResponse(
        id=track.id,
        global_id=track.global_id,
        entity_type=track.entity_type.value if hasattr(track.entity_type, 'value') else str(track.entity_type),
        current_camera_id=track.current_camera_id,
        current_sector=track.current_sector,
        plate_number=track.plate_number,
        face_identity_id=track.face_identity_id,
        face_identity_name=track.face_identity_name,
        confidence=track.confidence,
        identity_source=track.identity_source.value if hasattr(track.identity_source, 'value') else str(track.identity_source),
        first_seen=track.first_seen,
        last_seen=track.last_seen,
        is_active=track.is_active,
        total_observations=len(obs_list),
        observations=obs_list,
        journey_hops=journey_hops
    )

@router.get("/topology", response_model=List[CameraTopologyResponse])
async def get_camera_topology(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the active camera adjacency graph and transition thresholds.
    """
    links = topology_manager.get_all_links()
    res = []
    for idx, l in enumerate(links):
        res.append(CameraTopologyResponse(
            id=idx + 1,
            from_camera_id=l["from_camera_id"],
            to_camera_id=l["to_camera_id"],
            distance_meters=l["distance_meters"],
            min_travel_sec=l["min_travel_sec"],
            max_travel_sec=l["max_travel_sec"],
            direction=l["direction"],
            sector=l["sector"],
            is_active=l["is_active"]
        ))
    return res

@router.post("/topology", response_model=CameraTopologyResponse)
async def create_camera_topology_link(
    payload: CameraTopologyCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles([UserRole.ADMIN, UserRole.COMMANDER]))
):
    """
    Configures a spatial-temporal link between two cameras.
    """
    topology_manager.add_link(
        from_cam=payload.from_camera_id,
        to_cam=payload.to_camera_id,
        distance_m=payload.distance_meters,
        min_sec=payload.min_travel_sec,
        max_sec=payload.max_travel_sec,
        direction=payload.direction,
        sector=payload.sector
    )

    if payload.direction == "BIDIRECTIONAL":
        topology_manager.add_link(
            from_cam=payload.to_camera_id,
            to_cam=payload.from_camera_id,
            distance_m=payload.distance_meters,
            min_sec=payload.min_travel_sec,
            max_sec=payload.max_travel_sec,
            direction=payload.direction,
            sector=payload.sector
        )

    return CameraTopologyResponse(
        id=len(topology_manager.get_all_links()),
        from_camera_id=payload.from_camera_id,
        to_camera_id=payload.to_camera_id,
        distance_meters=payload.distance_meters,
        min_travel_sec=payload.min_travel_sec,
        max_travel_sec=payload.max_travel_sec,
        direction=payload.direction,
        sector=payload.sector,
        is_active=True
    )

@router.post("/simulate")
async def simulate_camera_transition(
    from_camera_id: int,
    to_camera_id: int,
    delta_seconds: float
):
    """
    Dry-run simulation to validate whether a camera transition is feasible.
    """
    is_valid, conf, link = topology_manager.validate_transition(
        from_cam=from_camera_id,
        to_cam=to_camera_id,
        delta_seconds=delta_seconds
    )
    return {
        "from_camera_id": from_camera_id,
        "to_camera_id": to_camera_id,
        "delta_seconds": delta_seconds,
        "is_feasible": is_valid,
        "confidence": round(conf, 3),
        "link_configured": link is not None,
        "link_metadata": link
    }

@router.post("/search")
async def search_cross_camera_entities(
    request: CrossCameraSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Search sighting history across all cameras by plate, face name, sector, or time range.
    """
    query = select(GlobalTrack).options(selectinload(GlobalTrack.observations)).order_by(desc(GlobalTrack.last_seen))

    if request.global_id:
        query = query.where(GlobalTrack.global_id == request.global_id)

    if request.plate_number:
        query = query.where(GlobalTrack.plate_number.ilike(f"%{request.plate_number}%"))

    if request.face_name:
        query = query.where(GlobalTrack.face_identity_name.ilike(f"%{request.face_name}%"))

    if request.sector:
        query = query.where(GlobalTrack.current_sector.ilike(f"%{request.sector}%"))

    if request.camera_id is not None:
        query = query.where(GlobalTrack.current_camera_id == request.camera_id)

    if request.start_time:
        query = query.where(GlobalTrack.last_seen >= request.start_time)

    if request.end_time:
        query = query.where(GlobalTrack.first_seen <= request.end_time)

    query = query.limit(request.limit)
    res = await db.execute(query)
    tracks = res.scalars().all()

    results = []
    for t in tracks:
        hops = []
        for obs in sorted(t.observations, key=lambda x: x.timestamp):
            hops.append({
                "camera_id": obs.camera_id,
                "camera_name": obs.camera_name,
                "sector": obs.sector_name,
                "timestamp": obs.timestamp.isoformat() if obs.timestamp else None,
                "duration_sec": obs.duration_sec
            })

        results.append({
            "global_id": t.global_id,
            "entity_type": t.entity_type.value if hasattr(t.entity_type, 'value') else str(t.entity_type),
            "current_camera_id": t.current_camera_id,
            "current_sector": t.current_sector,
            "plate_number": t.plate_number,
            "face_name": t.face_identity_name,
            "confidence": t.confidence,
            "identity_source": t.identity_source.value if hasattr(t.identity_source, 'value') else str(t.identity_source),
            "first_seen": t.first_seen.isoformat() if t.first_seen else None,
            "last_seen": t.last_seen.isoformat() if t.last_seen else None,
            "total_sightings": len(hops),
            "journey_hops": hops
        })

    return {
        "total_matches": len(results),
        "results": results
    }
