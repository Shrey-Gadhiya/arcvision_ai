import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.cross_camera import (
    GlobalTrack,
    TrackObservation,
    GlobalEntityType,
    IdentitySource,
    CameraTopology
)
from app.services.analytics.cross_camera.cross_camera_matcher import cross_camera_matcher
from app.services.analytics.cross_camera.base import PersonReIDAdapter, VehicleReIDAdapter

logger = logging.getLogger("arc_vision.cross_camera.global_manager")

class ActiveTrackState:
    def __init__(
        self,
        id: int,
        global_id: str,
        entity_type: GlobalEntityType,
        current_camera_id: int,
        current_sector: str,
        first_seen: float,
        last_seen: float,
        plate_number: Optional[str] = None,
        face_identity_id: Optional[int] = None,
        face_identity_name: Optional[str] = None,
        confidence: float = 1.0,
        identity_source: IdentitySource = IdentitySource.TOPOLOGY_TRANSITION
    ):
        self.id = id
        self.global_id = global_id
        self.entity_type = entity_type
        self.current_camera_id = current_camera_id
        self.current_sector = current_sector
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.plate_number = plate_number
        self.face_identity_id = face_identity_id
        self.face_identity_name = face_identity_name
        self.confidence = confidence
        self.identity_source = identity_source
        self.camera_hops: List[Dict[str, Any]] = []

class GlobalTrackManager:
    """
    Central Cross-Camera Identity & Global Track Orchestrator.
    """
    def __init__(self):
        # In-memory lookup: global_id -> ActiveTrackState
        self._active_tracks: Dict[str, ActiveTrackState] = {}
        self._person_counter: int = 100
        self._vehicle_counter: int = 100
        
        # Modular ReID Adapters (Report honest status)
        self.person_reid_adapter = PersonReIDAdapter()
        self.vehicle_reid_adapter = VehicleReIDAdapter()
        self.person_reid_adapter.load()
        self.vehicle_reid_adapter.load()

    def clear_active_tracks(self):
        """Flushes all in-memory cross-camera active tracks."""
        self._active_tracks.clear()
        logger.info("GlobalTrackManager active tracks cleared.")

    def generate_global_id(self, entity_type: GlobalEntityType) -> str:
        if entity_type == GlobalEntityType.VEHICLE:
            self._vehicle_counter += 1
            return f"GLOBAL-V-{self._vehicle_counter:05d}"
        else:
            self._person_counter += 1
            return f"GLOBAL-P-{self._person_counter:05d}"

    async def ingest_observation(
        self,
        camera_id: int,
        camera_name: str,
        local_track_id: int,
        object_class: str,
        box: List[float],
        timestamp: Optional[float] = None,
        duration_sec: float = 0.0,
        plate_number: Optional[str] = None,
        face_identity_id: Optional[int] = None,
        face_name: Optional[str] = None,
        sector_name: str = "Perimeter Sector",
        zones: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Ingests a local camera track observation and matches or registers a Global Track.
        Returns: (global_id, is_new_global_track, match_explanation)
        """
        now = timestamp or time.time()
        entity_type = GlobalEntityType.VEHICLE if object_class in ["car", "truck", "bus", "motorcycle"] else GlobalEntityType.PERSON
        active_list = list(self._active_tracks.values())

        # 1. Match against active global tracks
        match_res = cross_camera_matcher.find_best_match(
            active_global_tracks=active_list,
            entity_type=entity_type,
            camera_id=camera_id,
            observation_time=now,
            plate_number=plate_number,
            face_identity_id=face_identity_id,
            face_name=face_name
        )

        if match_res:
            global_id = match_res.global_id
            track_state = self._active_tracks.get(global_id)
            if track_state:
                track_state.last_seen = now
                track_state.current_camera_id = camera_id
                track_state.current_sector = sector_name
                if plate_number and not track_state.plate_number:
                    track_state.plate_number = plate_number
                if face_identity_id and not track_state.face_identity_id:
                    track_state.face_identity_id = face_identity_id
                    track_state.face_identity_name = face_name
                
                track_state.camera_hops.append({
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "timestamp": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%H:%M:%S"),
                    "zones": zones or []
                })

            if db:
                # Update DB
                res = await db.execute(select(GlobalTrack).where(GlobalTrack.global_id == global_id))
                gt = res.scalars().first()
                if gt:
                    gt.last_seen = datetime.fromtimestamp(now, tz=timezone.utc)
                    gt.current_camera_id = camera_id
                    gt.current_sector = sector_name
                    if plate_number:
                        gt.plate_number = plate_number
                    if face_identity_id:
                        gt.face_identity_id = face_identity_id
                        gt.face_identity_name = face_name
                    
                    obs = TrackObservation(
                        global_track_id=gt.id,
                        camera_id=camera_id,
                        local_track_id=local_track_id,
                        camera_name=camera_name,
                        sector_name=sector_name,
                        duration_sec=duration_sec,
                        bbox_json=json.dumps(box),
                        zones_json=json.dumps(zones or []),
                        timestamp=datetime.fromtimestamp(now, tz=timezone.utc)
                    )
                    db.add(obs)
                    await db.commit()

            return global_id, False, match_res.explanation

        # 2. Spawning new Global Track
        global_id = self.generate_global_id(entity_type)
        identity_src = IdentitySource.PLATE_MATCH if plate_number else (IdentitySource.FACE_MATCH if face_identity_id else IdentitySource.TOPOLOGY_TRANSITION)
        
        track_state = ActiveTrackState(
            id=len(self._active_tracks) + 1,
            global_id=global_id,
            entity_type=entity_type,
            current_camera_id=camera_id,
            current_sector=sector_name,
            first_seen=now,
            last_seen=now,
            plate_number=plate_number,
            face_identity_id=face_identity_id,
            face_identity_name=face_name,
            confidence=1.0,
            identity_source=identity_src
        )
        track_state.camera_hops.append({
            "camera_id": camera_id,
            "camera_name": camera_name,
            "timestamp": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%H:%M:%S"),
            "zones": zones or []
        })
        self._active_tracks[global_id] = track_state

        if db:
            gt = GlobalTrack(
                global_id=global_id,
                entity_type=entity_type,
                current_camera_id=camera_id,
                current_sector=sector_name,
                plate_number=plate_number,
                face_identity_id=face_identity_id,
                face_identity_name=face_name,
                confidence=1.0,
                identity_source=identity_src,
                first_seen=datetime.fromtimestamp(now, tz=timezone.utc),
                last_seen=datetime.fromtimestamp(now, tz=timezone.utc),
                is_active=True
            )
            db.add(gt)
            await db.commit()
            await db.refresh(gt)

            obs = TrackObservation(
                global_track_id=gt.id,
                camera_id=camera_id,
                local_track_id=local_track_id,
                camera_name=camera_name,
                sector_name=sector_name,
                duration_sec=duration_sec,
                bbox_json=json.dumps(box),
                zones_json=json.dumps(zones or []),
                timestamp=datetime.fromtimestamp(now, tz=timezone.utc)
            )
            db.add(obs)
            await db.commit()

        # Evict inactive global tracks older than 15 minutes from memory
        stale_keys = [k for k, v in self._active_tracks.items() if (now - v.last_seen) > 900.0]
        for k in stale_keys:
            del self._active_tracks[k]

        return global_id, True, "New Global Entity Initialized"

    def list_active_tracks(self) -> List[Dict[str, Any]]:
        return [
            {
                "global_id": t.global_id,
                "entity_type": t.entity_type.value,
                "current_camera_id": t.current_camera_id,
                "current_sector": t.current_sector,
                "first_seen": datetime.fromtimestamp(t.first_seen, tz=timezone.utc).isoformat(),
                "last_seen": datetime.fromtimestamp(t.last_seen, tz=timezone.utc).isoformat(),
                "plate_number": t.plate_number,
                "face_identity_id": t.face_identity_id,
                "face_identity_name": t.face_identity_name,
                "confidence": round(t.confidence, 2),
                "identity_source": t.identity_source.value,
                "hops_count": len(t.camera_hops),
                "hops": t.camera_hops
            }
            for t in self._active_tracks.values()
        ]

global_track_manager = GlobalTrackManager()
