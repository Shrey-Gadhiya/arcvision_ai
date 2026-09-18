import pytest
from datetime import datetime, timezone, timedelta
from app.services.semantic_search_engine import SemanticQueryParser, SemanticSearchService, InvestigationCaseService
from app.models.investigation import CaseStatus, CasePriority
from app.models.camera import Camera
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.anpr import ANPRRecord
from app.models.face import FaceRecord
from app.core.database import AsyncSessionLocal, init_db

@pytest.mark.anyio
async def test_semantic_query_parser():
    """Verify natural language query parsing into structured tokens and time ranges."""
    cams = {1: "Gate 1 - North", 2: "Gate 2 - South Entry", 3: "Warehouse Loading Dock"}

    # Test 1: Complex query with colors, vehicles, time, location
    q1 = "white car speeding near Gate 2 yesterday afternoon"
    parsed1 = SemanticQueryParser.parse_query(q1, available_cameras=cams)

    assert "car" in parsed1.object_classes
    assert "white" in parsed1.colors
    assert "speeding" in parsed1.action_terms
    assert 2 in parsed1.camera_ids
    assert "Gate 2 - South Entry" in parsed1.locations
    assert parsed1.time_range_start is not None
    assert parsed1.time_range_end is not None
    assert "Yesterday Afternoon" in (parsed1.temporal_expression or "")
    assert parsed1.parser_confidence >= 0.80

    # Test 2: Plate number and weapon threat
    q2 = "black SUV plate MH12DE1432 weapon detected at sector 1"
    parsed2 = SemanticQueryParser.parse_query(q2, available_cameras=cams)

    assert "car" in parsed2.object_classes
    assert "black" in parsed2.colors
    assert "MH12DE1432" in parsed2.plate_numbers
    assert "WEAPON_DETECTED" in parsed2.incident_types
    assert parsed2.parser_confidence >= 0.80

    # Test 3: Person fall or slip
    q3 = "person falling or slip accident today"
    parsed3 = SemanticQueryParser.parse_query(q3, available_cameras=cams)

    assert "person" in parsed3.object_classes
    assert "PERSON_FALL" in parsed3.incident_types
    assert parsed3.temporal_expression == "Today"


@pytest.mark.anyio
async def test_investigation_case_lifecycle_and_timeline():
    """Verify Case Dossier creation, findings pinning, timeline reconstruction, and report export."""
    await init_db()
    async with AsyncSessionLocal() as db:
        # 1. Create Camera with unique name
        import time
        cam_name = f"Gate 1 Forensic Cam {time.time_ns()}"
        cam = Camera(
            name=cam_name,
            rtsp_url="rtsp://192.168.1.180:554/live",
            location="Perimeter North",
            ptz_enabled=False
        )
        db.add(cam)
        await db.commit()
        await db.refresh(cam)

        # 2. Create Investigation Case
        case_data = {
            "title": "Unauthorized Night Intrusion Investigation",
            "description": "Multiple sightings of suspect near North Gate.",
            "priority": "HIGH",
            "lead_investigator": "Special Agent Miller",
            "hypothesis": "Suspect entered via Gate 1 perimeter fence during shift change.",
            "tags": ["perimeter_breach", "night_ops", "high_priority"]
        }
        case = await InvestigationCaseService.create_case(case_data, db)
        assert case.id is not None
        assert case.case_number.startswith("CASE-")
        assert case.status == CaseStatus.OPEN
        assert case.priority == CasePriority.HIGH

        # 3. Add Findings to Case
        now = datetime.now(timezone.utc)
        f1_data = {
            "item_type": "INCIDENT",
            "reference_id": "INC-2026-001",
            "camera_id": cam.id,
            "timestamp": now - timedelta(minutes=45),
            "title": "Perimeter Fence Breach Detected",
            "notes": "Tripwire trigger with bounding box correlation.",
            "metadata": {"threat_score": 92.0, "severity": "CRITICAL"}
        }
        f2_data = {
            "item_type": "ANPR",
            "reference_id": "PLT-1002",
            "camera_id": cam.id,
            "timestamp": now - timedelta(minutes=30),
            "title": "Suspicious Vehicle Sighting (MH12AB1234)",
            "notes": "Vehicle parked near Gate 1 for 15 minutes.",
            "metadata": {"plate": "MH12AB1234", "color": "dark grey"}
        }

        from app.models.investigation import CaseFinding
        import json
        finding1 = CaseFinding(
            case_id=case.id,
            item_type=f1_data["item_type"],
            reference_id=f1_data["reference_id"],
            camera_id=f1_data["camera_id"],
            timestamp=f1_data["timestamp"],
            title=f1_data["title"],
            notes=f1_data["notes"],
            metadata_json=json.dumps(f1_data["metadata"])
        )
        finding2 = CaseFinding(
            case_id=case.id,
            item_type=f2_data["item_type"],
            reference_id=f2_data["reference_id"],
            camera_id=f2_data["camera_id"],
            timestamp=f2_data["timestamp"],
            title=f2_data["title"],
            notes=f2_data["notes"],
            metadata_json=json.dumps(f2_data["metadata"])
        )
        db.add_all([finding1, finding2])
        await db.commit()

        # 4. Test Timeline Reconstruction
        timeline = await InvestigationCaseService.get_case_timeline(case.id, db)
        assert timeline.case_id == case.id
        assert timeline.total_events == 2
        assert len(timeline.camera_sequence) == 1
        assert timeline.camera_sequence[0]["camera_id"] == cam.id
        assert timeline.camera_sequence[0]["sightings_count"] == 2
        assert len(timeline.events) == 2

        # 5. Test Export Case Report
        report = await InvestigationCaseService.export_case_report(case.id, db)
        assert report.case.case_number == case.case_number
        assert report.summary_statistics["total_findings"] == 2
        assert report.summary_statistics["cameras_involved"] == 1
        assert "ARC VISION Dossier" in report.html_report
        assert "Perimeter Fence Breach" in report.html_report
        assert "Special Agent Miller" in report.html_report


@pytest.mark.anyio
async def test_investigation_api_endpoints():
    """Verify HTTP API endpoints for NL Search, Query Parsing, Case Dossier CRUD, and Export."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test Parse Query Endpoint
        parse_resp = await ac.post("/api/v1/investigation/parse-query", json={"query": "white car speeding near Gate 1 yesterday"})
        assert parse_resp.status_code == 200
        pq_data = parse_resp.json()
        assert "car" in pq_data["object_classes"]
        assert "white" in pq_data["colors"]
        assert "SPEEDING" in pq_data["incident_types"]
        assert pq_data["parser_confidence"] > 0.7

        # 2. Test NL Search Endpoint
        search_resp = await ac.post("/api/v1/investigation/nl-search", json={"query": "person detected today", "limit": 20})
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert "items" in search_data
        assert "parsed_query" in search_data

        # 3. Test Create Case
        create_resp = await ac.post("/api/v1/investigation/cases", json={
            "title": "API Test Case - High Security Zone",
            "description": "Investigating potential unauthorized access.",
            "priority": "CRITICAL",
            "lead_investigator": "Agent Carter",
            "hypothesis": "Suspicious loitering prior to alarm.",
            "tags": ["api_test", "critical"]
        })
        assert create_resp.status_code == 201
        case_info = create_resp.json()
        case_id = case_info["id"]
        assert case_info["priority"] == "CRITICAL"
        assert case_info["lead_investigator"] == "Agent Carter"

        # 4. Test List Cases
        list_resp = await ac.get("/api/v1/investigation/cases?search=API Test Case")
        assert list_resp.status_code == 200
        cases_list = list_resp.json()
        assert cases_list["total"] >= 1
        assert any(c["id"] == case_id for c in cases_list["items"])

        # 5. Test Add Finding to Case
        finding_resp = await ac.post(f"/api/v1/investigation/cases/{case_id}/findings", json={
            "item_type": "DETECTION",
            "title": "Person Loitering Near Vault Door",
            "notes": "Subject stayed in position for 120 seconds.",
            "metadata": {"dwell_sec": 120, "confidence": 0.94}
        })
        assert finding_resp.status_code == 201
        finding_data = finding_resp.json()
        finding_id = finding_data["id"]
        assert finding_data["item_type"] == "DETECTION"

        # 6. Test Get Case Timeline
        timeline_resp = await ac.get(f"/api/v1/investigation/cases/{case_id}/timeline")
        assert timeline_resp.status_code == 200
        timeline_data = timeline_resp.json()
        assert timeline_data["total_events"] >= 1
        assert timeline_data["events"][0]["title"] == "Person Loitering Near Vault Door"

        # 7. Test Export Case (JSON and HTML)
        export_resp = await ac.get(f"/api/v1/investigation/cases/{case_id}/export")
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["case"]["id"] == case_id
        assert "html_report" in export_data

        html_resp = await ac.get(f"/api/v1/investigation/cases/{case_id}/export?format=html")
        assert html_resp.status_code == 200
        assert "ARC VISION Dossier" in html_resp.text

        # 8. Test Update Case
        update_resp = await ac.put(f"/api/v1/investigation/cases/{case_id}", json={
            "status": "UNDER_INVESTIGATION",
            "hypothesis": "Updated: Subject was authorized contractor awaiting escort."
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "UNDER_INVESTIGATION"

        # 9. Test Remove Finding
        del_finding_resp = await ac.delete(f"/api/v1/investigation/cases/{case_id}/findings/{finding_id}")
        assert del_finding_resp.status_code == 200

        # 10. Test Delete Case
        del_case_resp = await ac.delete(f"/api/v1/investigation/cases/{case_id}")
        assert del_case_resp.status_code == 200

