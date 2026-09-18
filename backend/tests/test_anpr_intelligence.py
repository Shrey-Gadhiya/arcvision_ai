import os
import sys
import pytest
import numpy as np
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

# Ensure backend root is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import AsyncSessionLocal, init_db, Base, engine
from app.models.camera import Camera, CameraStatus, StreamType, CameraRecordingMode
from app.models.anpr import ANPRRecord, ANPRWatchlist, PlateWatchlistCategory, WatchlistPriority, PlateValidationStatus
from app.models.user import User, UserRole
from app.services.ai.anpr.normalizer import clean_raw_plate, normalize_indian_plate
from app.services.ai.anpr.validators import IndianPlateValidator
from app.services.ai.anpr.base import (
    BasePlateDetectorAdapter,
    BasePlateOCRAdapter,
    PlateDetectionResult,
    OCRResult,
    AdapterStatus
)
from app.services.ai.anpr.adapters import (
    HeuristicPlateDetectorAdapter,
    UnavailablePlateDetectorAdapter,
    UnavailableOCRAdapter
)
from app.services.ai.anpr.service import PlateRecognitionService
from app.services.analytics.vehicle_intelligence import VehicleIntelligenceService
from app.api.v1.auth import create_access_token

@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"

@pytest.fixture
def auth_headers():
    token = create_access_token(subject="admin", role="ADMIN")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def setup_db_for_test():
    pass


# ============================================================================
# 1. Normalization & Character Correction Tests
# ============================================================================

def test_clean_raw_plate():
    assert clean_raw_plate(" DL - 01 - AB - 1234 ") == "DL01AB1234"
    assert clean_raw_plate("hr.26.dk.8392") == "HR26DK8392"
    assert clean_raw_plate("") == ""

def test_indian_plate_normalization():
    # Positional character corrections:
    # '0' in state code slot 0 -> 'O'
    # 'O' in district code slot 2 -> '0'
    raw = "0L01AB1234"
    norm, meta = normalize_indian_plate(raw)
    assert norm == "OL01AB1234"

    # Bharat series: 228H1234AA -> 22BH1234AA (8 corrected to B in BH)
    norm_bh, meta_bh = normalize_indian_plate("228H1234AA")
    assert norm_bh == "22BH1234AA"
    assert meta_bh["schema"] == "BHARAT_SERIES"

# ============================================================================
# 2. Indian Plate Validator Tests
# ============================================================================

def test_indian_standard_valid_plates():
    valid_plates = [
        "DL01AB1234",
        "HR26DK8392",
        "MH12DE1432",
        "KA03MD5678",
        "TN09BK4321",
        "GJ01AB1234",
        "UP32AB1234",
        "WB02AB1234",
        "PB65X4422"
    ]
    for p in valid_plates:
        res = IndianPlateValidator.validate(p)
        assert res.status == "VALID", f"Plate {p} should be valid: {res.diagnostics}"
        assert res.format_name == "INDIAN_STANDARD"
        assert res.confidence >= 0.90

def test_bharat_series_valid_plates():
    bh_plates = [
        "22BH1234AA",
        "21BH9999Z",
        "23BH0001AB"
    ]
    for p in bh_plates:
        res = IndianPlateValidator.validate(p)
        assert res.status == "VALID", f"BH Plate {p} should be valid: {res.diagnostics}"
        assert res.format_name == "BHARAT_SERIES"
        assert res.confidence >= 0.95

def test_defence_and_uncertain_plates():
    res_def = IndianPlateValidator.validate("21D123456A")
    assert res_def.status == "VALID"
    assert res_def.format_name == "DEFENCE_BORDER"

    # Valid alphanumeric syntax but unknown state code
    res_unc = IndianPlateValidator.validate("ZZ01AB1234")
    assert res_unc.status == "UNCERTAIN"

    # Completely invalid
    res_inv = IndianPlateValidator.validate("??$$")
    assert res_inv.status == "INVALID"

# ============================================================================
# 3. Adapter Contracts & Explicit Unavailable Reporting
# ============================================================================

def test_heuristic_detector_adapter():
    detector = HeuristicPlateDetectorAdapter()
    assert detector.load() is True
    dummy_veh = np.zeros((200, 200, 3), dtype=np.uint8)
    dets = detector.detect_plates(dummy_veh)
    assert len(dets) == 1
    assert dets[0].confidence > 0.5
    assert dets[0].plate_crop is not None
    assert detector.unload() is True

def test_unavailable_adapters_honest_reporting():
    un_det = UnavailablePlateDetectorAdapter()
    assert un_det.status == AdapterStatus.NOT_CONFIGURED
    assert un_det.detect_plates(np.zeros((100, 100, 3), dtype=np.uint8)) == []

    un_ocr = UnavailableOCRAdapter()
    assert un_ocr.status == AdapterStatus.UNAVAILABLE
    res = un_ocr.read_plate(np.zeros((50, 100, 3), dtype=np.uint8))
    assert res.status == "UNAVAILABLE"
    assert res.raw_text == ""  # Zero synthetic text invented

# ============================================================================
# 4. Vehicle Intelligence Motion Dynamics
# ============================================================================

def test_vehicle_intelligence_stationary_detection():
    service = VehicleIntelligenceService()
    service.stationary_threshold_sec = 5.0

    # Moving vehicle
    dyn_moving = service.evaluate_motion_dynamics(
        camera_id=1,
        track_id=10,
        centroid=(0.1, 0.1),
        dwell_sec=2.0,
        timestamp=1.0
    )
    assert dyn_moving["is_stationary"] is False

    # Simulate 6 stationary frames with 10s dwell
    for i in range(6):
        dyn_stat = service.evaluate_motion_dynamics(
            camera_id=1,
            track_id=20,
            centroid=(0.5, 0.5),
            dwell_sec=10.0,
            timestamp=2.0 + i
        )

    assert dyn_stat["is_stationary"] is True
    assert dyn_stat["dwell_sec"] == 10.0

# ============================================================================
# 5. Service Orchestration & Watchlist Matching
# ============================================================================

class MockTestingOCRAdapter(BasePlateOCRAdapter):
    """Testing OCR adapter to feed controlled plate text."""
    def __init__(self, target_text: str = "DL01AB1234"):
        super().__init__(name="mock_test_ocr", device="test")
        self.target_text = target_text
        self.status = AdapterStatus.LOADED

    def load(self) -> bool:
        return True

    def unload(self) -> bool:
        return True

    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        return OCRResult(raw_text=self.target_text, confidence=0.96, status="SUCCESS")

@pytest.mark.anyio
async def test_anpr_service_process_vehicle():
    await init_db()

    service = PlateRecognitionService()
    service.detector_adapter = HeuristicPlateDetectorAdapter()
    service.ocr_adapter = MockTestingOCRAdapter("HR26DK8392")

    # Get or create dummy camera in DB
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        cam_res = await session.execute(select(Camera).limit(1))
        cam = cam_res.scalars().first()
        if not cam:
            cam = Camera(
                name="ANPR Test Camera Gate 1",
                rtsp_url="rtsp://dummy/test",
                stream_type=StreamType.SYNTHETIC,
                group_name="Perimeter",
                location="Gate 1"
            )
            session.add(cam)
            await session.commit()
            await session.refresh(cam)
        cam_id = cam.id

        # Add plate to watchlist if not present
        w_res = await session.execute(select(ANPRWatchlist).where(ANPRWatchlist.plate_number == "HR26DK8392"))
        watch = w_res.scalars().first()
        if not watch:
            watch = ANPRWatchlist(
                plate_number="HR26DK8392",
                category=PlateWatchlistCategory.STOLEN,
                priority=WatchlistPriority.CRITICAL,
                notes="Flagged stolen SUV"
            )
            session.add(watch)
            await session.commit()

    # Process vehicle
    dummy_crop = np.zeros((150, 150, 3), dtype=np.uint8)
    dummy_full = np.zeros((720, 1280, 3), dtype=np.uint8)

    res = await service.process_vehicle(
        camera_id=cam_id,
        camera_name="Main Gate Cam",
        track_id=101,
        vehicle_class="car",
        vehicle_crop=dummy_crop,
        full_frame=dummy_full,
        dwell_duration_sec=5.0,
        is_stationary=False
    )

    assert res is not None
    assert res["plate_number"] == "HR26DK8392"
    assert res["is_matched"] is True
    assert res["validation_status"] == "VALID"

    # Verify DB persistence
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        q = await session.execute(select(ANPRRecord).where(ANPRRecord.plate_number == "HR26DK8392"))
        record = q.scalars().first()
        assert record is not None
        assert record.is_matched is True
        assert record.watchlist_category == "STOLEN"

# ============================================================================
# 6. REST API Endpoints & RBAC Tests
# ============================================================================

@pytest.mark.anyio
async def test_anpr_status_api():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/anpr/status")
        assert res.status_code == 200
        data = res.json()
        assert "detector_adapter" in data
        assert "ocr_adapter" in data
        assert "validation_capabilities" in data

@pytest.mark.anyio
async def test_anpr_watchlist_crud_and_rbac(auth_headers):
    await init_db()

    # Create admin user in DB for audit log FK
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        u_res = await session.execute(select(User).where(User.username == "admin"))
        if not u_res.scalars().first():
            user = User(
                username="admin",
                email="admin@arcvision.ai",
                hashed_password="hashed_dummy",
                role=UserRole.ADMIN,
                is_active=True
            )
            session.add(user)
            await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Add plate to watchlist
        create_res = await client.post(
            "/api/v1/anpr/watchlist",
            json={
                "plate_number": "DL01AB9999",
                "category": "SUSPECT",
                "priority": "HIGH",
                "vehicle_model": "White Scorpio",
                "notes": "Suspect in perimeter surveillance case"
            },
            headers=auth_headers
        )
        assert create_res.status_code == 201
        created_id = create_res.json()["id"]

        # 2. List watchlist
        list_res = await client.get("/api/v1/anpr/watchlist")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 3. Query plate
        query_res = await client.get("/api/v1/anpr/query/DL01AB9999")
        assert query_res.status_code == 200
        q_data = query_res.json()
        assert q_data["is_flagged"] is True
        assert q_data["normalized_plate"] == "DL01AB9999"

        # 4. Update watchlist
        update_res = await client.put(
            f"/api/v1/anpr/watchlist/{created_id}",
            json={"priority": "CRITICAL", "notes": "Escalated threat"},
            headers=auth_headers
        )
        assert update_res.status_code == 200
        assert update_res.json()["priority"] == "CRITICAL"

        # 5. Delete from watchlist
        del_res = await client.delete(f"/api/v1/anpr/watchlist/{created_id}", headers=auth_headers)
        assert del_res.status_code == 204

@pytest.mark.anyio
async def test_anpr_records_and_search_api():
    await init_db()

    # Get or create camera
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        cam_res = await session.execute(select(Camera).limit(1))
        cam = cam_res.scalars().first()
        if not cam:
            cam = Camera(
                name="ANPR Search Cam North Gate",
                rtsp_url="rtsp://dummy/test2",
                stream_type=StreamType.SYNTHETIC,
                group_name="Perimeter",
                location="Gate 2"
            )
            session.add(cam)
            await session.commit()
            await session.refresh(cam)
        cam_id = cam.id

        rec = ANPRRecord(
            camera_id=cam_id,
            track_id=202,
            raw_text="22BH1234AA",
            plate_number="22BH1234AA",
            confidence=0.97,
            validation_status=PlateValidationStatus.VALID,
            validation_format="BHARAT_SERIES",
            vehicle_type="car",
            is_matched=False
        )
        session.add(rec)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List records
        list_res = await client.get("/api/v1/anpr/records")
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

        # Multi-criteria search
        search_res = await client.post(
            "/api/v1/anpr/search",
            json={"plate_number": "22BH", "vehicle_type": "car"}
        )
        assert search_res.status_code == 200
        assert search_res.json()["total"] >= 1
        assert search_res.json()["items"][0]["plate_number"] == "22BH1234AA"

@pytest.mark.anyio
async def test_vehicle_intelligence_analytics_api():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/anpr/vehicles/analytics?hours=24")
        assert res.status_code == 200
        data = res.json()
        assert "total_sightings" in data
        assert "unique_plates" in data
        assert "vehicle_class_distribution" in data

