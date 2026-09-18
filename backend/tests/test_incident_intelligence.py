import pytest
from app.services.analytics.incident_intelligence import IncidentIntelligenceEngine
from app.models.incident import IncidentSeverity, IncidentStatus

def test_incident_correlation():
    engine = IncidentIntelligenceEngine()

    # Case 1: Low-signal detection (no rules fired, low dwell) -> Should NOT produce incident
    res1 = engine.correlate(
        camera_id=1,
        camera_name="CAM-01",
        track_id=5,
        object_class="person",
        events=[],
        dwell_sec=2.0,
        is_pacing=False,
        is_night=False,
        active_zones=[]
    )
    assert res1 is None

    # Case 2: Multi-factor breach (Fence crossing + Restricted Zone + Night + Pacing) -> Must produce CRITICAL incident
    high_threat_events = [
        {"event_type": "VIRTUAL_FENCE_CROSSING", "rule_id": 101},
        {"event_type": "ZONE_INTRUSION", "rule_id": 102}
    ]
    res2 = engine.correlate(
        camera_id=1,
        camera_name="CAM-01",
        track_id=12,
        object_class="person",
        events=high_threat_events,
        dwell_sec=25.0,
        is_pacing=True,
        is_night=True,
        active_zones=[{"zone_type": "RESTRICTED", "name": "Restricted Zone Sector 4"}]
    )

    assert res2 is not None
    assert res2["severity"] == IncidentSeverity.CRITICAL
    assert res2["status"] == IncidentStatus.NEW
    assert res2["threat_score"] >= 85.0
    assert "person" in res2["summary"].lower()
    assert res2["incident_code"].startswith("INC-")
