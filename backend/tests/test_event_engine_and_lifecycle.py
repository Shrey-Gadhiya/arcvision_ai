import pytest
import json
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.api.v1.incidents import VALID_TRANSITIONS

def test_incident_status_transitions_validity():
    # Verify DETECTED transitions
    assert IncidentStatus.TRIAGED in VALID_TRANSITIONS[IncidentStatus.DETECTED]
    assert IncidentStatus.ACKNOWLEDGED in VALID_TRANSITIONS[IncidentStatus.DETECTED]
    assert IncidentStatus.CLOSED in VALID_TRANSITIONS[IncidentStatus.DETECTED]

    # Verify TRIAGED transitions
    assert IncidentStatus.ACKNOWLEDGED in VALID_TRANSITIONS[IncidentStatus.TRIAGED]
    assert IncidentStatus.INVESTIGATING in VALID_TRANSITIONS[IncidentStatus.TRIAGED]

    # Verify INVESTIGATING transitions
    assert IncidentStatus.RESOLVED in VALID_TRANSITIONS[IncidentStatus.INVESTIGATING]
    assert IncidentStatus.CLOSED in VALID_TRANSITIONS[IncidentStatus.INVESTIGATING]

    # Verify RESOLVED transitions
    assert IncidentStatus.CLOSED in VALID_TRANSITIONS[IncidentStatus.RESOLVED]
    assert IncidentStatus.INVESTIGATING in VALID_TRANSITIONS[IncidentStatus.RESOLVED]

def test_invalid_transitions_rejected():
    # Direct jump from DETECTED to RESOLVED is invalid (must be triaged/investigated first)
    assert IncidentStatus.RESOLVED not in VALID_TRANSITIONS[IncidentStatus.DETECTED]

def test_incident_model_lifecycle_fields():
    inc = Incident(
        incident_code="INC-2026-TEST-01",
        title="Test Perimeter Breach",
        summary="Automated test incident",
        incident_type="INTRUSION",
        camera_id=1,
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.DETECTED,
        threat_score=92.0,
        assigned_to="commander_alpha",
        transition_history_json=json.dumps([{"from": "DETECTED", "to": "TRIAGED", "user": "operator"}]),
        operator_notes_json=json.dumps([{"user": "operator", "text": "Dispatched ground patrol"}])
    )
    assert inc.incident_code == "INC-2026-TEST-01"
    assert inc.status == IncidentStatus.DETECTED
    assert inc.assigned_to == "commander_alpha"
    
    history = json.loads(inc.transition_history_json)
    assert len(history) == 1
    assert history[0]["to"] == "TRIAGED"
