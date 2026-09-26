import time
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.cross_camera import (
    GlobalTrack,
    TrackObservation,
    GlobalEntityType,
    IdentitySource
)
from app.services.analytics.cross_camera.base import PersonReIDAdapter, VehicleReIDAdapter
from app.services.analytics.cross_camera.topology_manager import topology_manager
from app.services.analytics.cross_camera.cross_camera_matcher import cross_camera_matcher
from app.services.analytics.cross_camera.global_track_manager import GlobalTrackManager, ActiveTrackState

def test_reid_adapter_contracts():
    """Verify that ReID adapters report honest status without fabricating results."""
    person_reid = PersonReIDAdapter()
    vehicle_reid = VehicleReIDAdapter()

    # Person ReID loads real deep feature extractor, while Vehicle ReID honestly remains standby
    assert person_reid.is_loaded is True
    assert vehicle_reid.load() is False

    p_status = person_reid.get_status()
    v_status = vehicle_reid.get_status()

    assert p_status["status"] in ["LOADED", "ACTIVE", "STANDBY", "NOT_CONFIGURED"]
    assert v_status["status"] in ["STANDBY", "NOT_CONFIGURED", "STANDBY / NOT_CONFIGURED"]
    assert p_status["task"] == "PERSON_REID"
    assert v_status["task"] == "VEHICLE_REID"

    # Extraction returns None when real weights are not configured
    assert person_reid.extract_embedding(None) is None
    assert vehicle_reid.extract_embedding(None) is None

def test_topology_manager_transitions():
    """Verify spatial-temporal transition feasibility calculations."""
    topology_manager.initialize_defaults()

    # Direct adjacent transition Cam 1 -> Cam 2 (configured: min 3.0s, max 45.0s)
    is_valid, conf, link = topology_manager.validate_transition(from_cam=1, to_cam=2, delta_seconds=15.0)
    assert is_valid is True
    assert conf >= 0.85
    assert link is not None

    # Impossibly fast transition (1.0s < min 3.0s) -> Rejected
    is_valid_fast, conf_fast, _ = topology_manager.validate_transition(from_cam=1, to_cam=2, delta_seconds=1.0)
    assert is_valid_fast is False
    assert conf_fast <= 0.20

    # Same camera -> always valid
    is_same, conf_same, _ = topology_manager.validate_transition(from_cam=2, to_cam=2, delta_seconds=5.0)
    assert is_same is True
    assert conf_same >= 0.90

def test_cross_camera_plate_correlation():
    """Verify explicit license plate multi-camera correlation."""
    now = time.time()
    t1 = ActiveTrackState(
        id=1,
        global_id="GLOBAL-V-00101",
        entity_type=GlobalEntityType.VEHICLE,
        current_camera_id=1,
        current_sector="Perimeter Gate",
        first_seen=now - 20.0,
        last_seen=now - 10.0,
        plate_number="DL01AB1234",
        identity_source=IdentitySource.PLATE_MATCH
    )

    # Plate match on Cam 2
    match = cross_camera_matcher.find_best_match(
        active_global_tracks=[t1],
        entity_type=GlobalEntityType.VEHICLE,
        camera_id=2,
        observation_time=now,
        plate_number="DL-01-AB-1234"  # Normalized match
    )

    assert match is not None
    assert match.global_id == "GLOBAL-V-00101"
    assert match.confidence >= 0.99
    assert match.source == IdentitySource.PLATE_MATCH

def test_cross_camera_face_correlation():
    """Verify explicit biometric face identity multi-camera correlation."""
    now = time.time()
    t1 = ActiveTrackState(
        id=2,
        global_id="GLOBAL-P-00101",
        entity_type=GlobalEntityType.PERSON,
        current_camera_id=1,
        current_sector="Main Gate",
        first_seen=now - 30.0,
        last_seen=now - 15.0,
        face_identity_id=42,
        face_identity_name="Inspector Sharma",
        identity_source=IdentitySource.FACE_MATCH
    )

    # Face match on Cam 3
    match = cross_camera_matcher.find_best_match(
        active_global_tracks=[t1],
        entity_type=GlobalEntityType.PERSON,
        camera_id=3,
        observation_time=now,
        face_identity_id=42,
        face_name="Inspector Sharma"
    )

    assert match is not None
    assert match.global_id == "GLOBAL-P-00101"
    assert match.confidence >= 0.98
    assert match.source == IdentitySource.FACE_MATCH

def test_cross_camera_conflict_resolution():
    """Verify that conflicting plates or faces are NEVER merged."""
    now = time.time()
    t1 = ActiveTrackState(
        id=3,
        global_id="GLOBAL-V-00102",
        entity_type=GlobalEntityType.VEHICLE,
        current_camera_id=1,
        current_sector="Main Gate",
        first_seen=now - 20.0,
        last_seen=now - 10.0,
        plate_number="HR26DK8888"
    )

    # Contradictory plate "UP14BT9999" arriving on Cam 2 -> Must NOT match t1
    match = cross_camera_matcher.find_best_match(
        active_global_tracks=[t1],
        entity_type=GlobalEntityType.VEHICLE,
        camera_id=2,
        observation_time=now,
        plate_number="UP14BT9999"
    )

    assert match is None

def test_global_track_manager_lifecycle():
    """Verify end-to-end global track creation, observation ingestion, and journey hops."""
    async def _run():
        mgr = GlobalTrackManager()
        now = time.time()

        # 1. First sighting on Camera 1
        gid1, is_new1, _ = await mgr.ingest_observation(
            camera_id=1,
            camera_name="Perimeter Gate Alpha",
            local_track_id=12,
            object_class="car",
            box=[0.1, 0.2, 0.4, 0.5],
            timestamp=now,
            plate_number="DL01XY9999",
            sector_name="Sector North"
        )
        assert is_new1 is True
        assert gid1.startswith("GLOBAL-V-")

        # 2. Sighting on Camera 2 with same plate 12 seconds later -> Correlates to gid1
        gid2, is_new2, expl = await mgr.ingest_observation(
            camera_id=2,
            camera_name="Sterile Buffer Zone",
            local_track_id=45,
            object_class="car",
            box=[0.2, 0.3, 0.5, 0.6],
            timestamp=now + 12.0,
            plate_number="DL01XY9999",
            sector_name="Sector North"
        )
        assert is_new2 is False
        assert gid2 == gid1
        assert "Plate Match" in expl

        # Check active track history
        tracks = mgr.list_active_tracks()
        assert len(tracks) >= 1
        match_track = next(t for t in tracks if t["global_id"] == gid1)
        assert match_track["hops_count"] == 2
        assert match_track["current_camera_id"] == 2

    asyncio.run(_run())

def test_cross_camera_api_endpoints():
    """Verify FastAPI cross-camera endpoints."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Subsystem status
            status_res = await client.get("/api/v1/cross-camera/status")
            assert status_res.status_code == 200
            data = status_res.json()
            assert data["status"] == "OPERATIONAL"
            assert "plate_correlation" in data["subsystems"]
            assert "face_correlation" in data["subsystems"]
            assert "appearance_person_reid" in data["subsystems"]
            assert data["subsystems"]["appearance_person_reid"]["status"] in ["LOADED", "ACTIVE", "STANDBY", "NOT_CONFIGURED", "STANDBY / NOT_CONFIGURED"]

            # 2. Topology list
            topo_res = await client.get("/api/v1/cross-camera/topology")
            assert topo_res.status_code == 200
            links = topo_res.json()
            assert len(links) > 0

            # 3. Simulate transition
            sim_res = await client.post("/api/v1/cross-camera/simulate?from_camera_id=1&to_camera_id=2&delta_seconds=15.0")
            assert sim_res.status_code == 200
            sim_data = sim_res.json()
            assert sim_data["is_feasible"] is True

            # 4. Infeasible transition
            sim_res2 = await client.post("/api/v1/cross-camera/simulate?from_camera_id=1&to_camera_id=2&delta_seconds=1.0")
            assert sim_res2.status_code == 200
            assert sim_res2.json()["is_feasible"] is False

    asyncio.run(_run())
