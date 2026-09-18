import time
import pytest
import numpy as np

from app.services.ai.base import Detection
from app.services.analytics.behavior.base import (
    BehaviorFeatureExtractor,
    BehaviorEvent,
    AnalyzerStatus
)
from app.services.analytics.behavior.analyzers import (
    LoiteringAnalyzer,
    StationaryObjectAnalyzer,
    WrongWayMovementAnalyzer,
    RestrictedAreaBehaviorAnalyzer,
    NightMovementAnalyzer,
    CrowdDensityAnalyzer,
    AbandonedObjectAnalyzer,
    RemovedObjectAnalyzer,
    RepeatedMovementAnalyzer,
    RapidMovementAnalyzer,
    SuspiciousRouteAnalyzer
)
from app.services.analytics.behavior.engine import BehaviorAnalyticsEngine
from app.services.analytics.incident_intelligence import IncidentIntelligenceEngine
from app.services.analytics.rule_evaluator import RuleEvaluator
from app.models.rule import Rule, RuleEventType, RuleSeverity

# 1. Feature Extractor Tests
def test_feature_extractor_kinematics():
    # Trajectory moving linearly from (0.1, 0.1) to (0.5, 0.4) over 2 seconds
    traj = [
        (0.1, 0.1, 0.0),
        (0.3, 0.25, 1.0),
        (0.5, 0.4, 2.0)
    ]

    disp = BehaviorFeatureExtractor.compute_displacement(traj)
    assert abs(disp - 0.5) < 0.01

    speed = BehaviorFeatureExtractor.compute_speed(traj)
    assert speed > 0.1

    heading = BehaviorFeatureExtractor.compute_heading_vector(traj)
    assert heading[0] > 0 and heading[1] > 0

    reversals = BehaviorFeatureExtractor.compute_direction_reversals(traj)
    assert reversals == 0

def test_feature_extractor_reversals():
    # Oscillating trajectory A -> B -> A -> B -> A -> B
    traj = [
        (0.1, 0.5, 0.0), (0.4, 0.5, 1.0),
        (0.1, 0.5, 2.0), (0.4, 0.5, 3.0),
        (0.1, 0.5, 4.0), (0.4, 0.5, 5.0)
    ]
    reversals = BehaviorFeatureExtractor.compute_direction_reversals(traj)
    assert reversals >= 3

# 2. Loitering Analyzer
def test_loitering_analyzer():
    analyzer = LoiteringAnalyzer(default_dwell_sec=10.0, max_radius=0.20)
    det = Detection(
        class_name="person",
        confidence=0.9,
        box=[0.2, 0.2, 0.3, 0.4],
        track_id=10,
        attributes={
            "dwell_sec": 12.0,
            "trajectory": [(0.25, 0.3, 0.0), (0.26, 0.31, 10.0)]
        }
    )
    zones = {10: [{"id": 1, "name": "Sterile Buffer", "loitering_time_sec": 10.0}]}
    events = analyzer.evaluate(1, [det], zones, {})
    assert len(events) == 1
    assert events[0].event_type == "LOITERING"
    assert events[0].details["dwell_sec"] == 12.0

# 3. Stationary Object & Vehicle Analyzer
def test_stationary_vehicle_and_object():
    analyzer = StationaryObjectAnalyzer(vehicle_dwell_thresh=10.0, object_dwell_thresh=8.0)
    
    # Stopped vehicle
    car_det = Detection(
        class_name="car",
        confidence=0.95,
        box=[0.1, 0.1, 0.3, 0.3],
        track_id=1,
        attributes={"is_stationary": True, "dwell_sec": 12.0}
    )
    # Stopped bag
    bag_det = Detection(
        class_name="backpack",
        confidence=0.88,
        box=[0.5, 0.5, 0.6, 0.6],
        track_id=2,
        attributes={"is_stationary": True, "dwell_sec": 9.0}
    )

    events = analyzer.evaluate(1, [car_det, bag_det], {}, {})
    assert len(events) == 2
    types = {e.event_type for e in events}
    assert "STATIONARY_VEHICLE" in types
    assert "STATIONARY_OBJECT" in types

# 4. Wrong-Way Movement
def test_wrong_way_movement():
    analyzer = WrongWayMovementAnalyzer()
    det = Detection(class_name="car", confidence=0.9, box=[0.1, 0.1, 0.2, 0.2], track_id=5)
    breaches = {
        5: [{
            "tripwire": {"id": 1, "name": "Exit Gate Lane 1", "direction": "A_TO_B"},
            "crossing_direction": "B_TO_A"
        }]
    }
    events = analyzer.evaluate(1, [det], {}, breaches)
    assert len(events) == 1
    assert events[0].event_type == "WRONG_WAY"
    assert events[0].details["expected_direction"] == "A_TO_B"
    assert events[0].details["actual_direction"] == "B_TO_A"

# 5. Restricted Area Behavior
def test_restricted_area_behavior():
    analyzer = RestrictedAreaBehaviorAnalyzer()
    det = Detection(class_name="person", confidence=0.9, box=[0.1, 0.1, 0.2, 0.2], track_id=7)
    zones = {7: [{"id": 3, "name": "Ammunition Depot", "zone_type": "RESTRICTED"}]}
    events = analyzer.evaluate(1, [det], zones, {})
    assert len(events) == 1
    assert events[0].event_type == "RESTRICTED_ZONE_ACTIVITY"
    assert events[0].zone_name == "Ammunition Depot"

# 6. Night Movement Analyzer
def test_night_movement_analyzer():
    analyzer = NightMovementAnalyzer()
    det = Detection(class_name="person", confidence=0.85, box=[0.1, 0.1, 0.2, 0.2], track_id=8)
    # Context with is_night_mode = True
    events_night = analyzer.evaluate(1, [det], {}, {}, context={"is_night_mode": True})
    assert len(events_night) == 1
    assert events_night[0].event_type == "NIGHT_MOVEMENT"

    # Context with is_night_mode = False
    events_day = analyzer.evaluate(1, [det], {}, {}, context={"is_night_mode": False})
    assert len(events_day) == 0

# 7. Crowd Density Analyzer
def test_crowd_density_analyzer():
    analyzer = CrowdDensityAnalyzer(crowd_threshold=3)
    p1 = Detection(class_name="person", confidence=0.9, box=[0.1, 0.1, 0.2, 0.2], track_id=1)
    p2 = Detection(class_name="person", confidence=0.9, box=[0.12, 0.12, 0.22, 0.22], track_id=2)
    p3 = Detection(class_name="person", confidence=0.9, box=[0.14, 0.14, 0.24, 0.24], track_id=3)

    zone_info = [{"id": 10, "name": "Checkpoint Alpha"}]
    zones = {1: zone_info, 2: zone_info, 3: zone_info}

    events = analyzer.evaluate(1, [p1, p2, p3], zones, {})
    assert len(events) == 1
    assert events[0].event_type == "CROWD_DENSITY"
    assert events[0].details["people_count"] == 3

# 8. Abandoned Object Analyzer
def test_abandoned_object_analyzer():
    analyzer = AbandonedObjectAnalyzer(min_abandoned_sec=5.0, separation_dist=0.20)
    bag = Detection(
        class_name="backpack",
        confidence=0.9,
        box=[0.5, 0.5, 0.6, 0.6],
        track_id=101,
        attributes={"dwell_sec": 6.0, "centroid": (0.55, 0.55)}
    )
    # Person far away at (0.1, 0.1) -> dist = ~0.63 > 0.20
    person = Detection(
        class_name="person",
        confidence=0.9,
        box=[0.05, 0.05, 0.15, 0.15],
        track_id=1,
        attributes={"centroid": (0.1, 0.1)}
    )

    events = analyzer.evaluate(1, [bag, person], {}, {})
    assert len(events) == 1
    assert events[0].event_type == "ABANDONED_OBJECT"
    assert events[0].details["dwell_sec"] == 6.0

# 9. Removed Object Analyzer
def test_removed_object_analyzer():
    analyzer = RemovedObjectAnalyzer(persistence_sec=0.1)
    # Frame 1: Object present for 12 seconds
    box_det = Detection(
        class_name="box",
        confidence=0.9,
        box=[0.3, 0.3, 0.4, 0.4],
        track_id=55,
        attributes={"dwell_sec": 12.0}
    )
    analyzer.evaluate(1, [box_det], {}, {})
    assert 55 in analyzer._stationary_items

    # Frame 2: Object disappears
    time.sleep(0.15)
    events = analyzer.evaluate(1, [], {}, {})
    assert len(events) == 1
    assert events[0].event_type == "REMOVED_OBJECT"
    assert events[0].track_id == 55

# 10. Repeated Movement (Pacing) Analyzer
def test_repeated_movement_analyzer():
    analyzer = RepeatedMovementAnalyzer(min_reversals=3, min_dwell=5.0)
    det = Detection(
        class_name="person",
        confidence=0.9,
        box=[0.2, 0.2, 0.3, 0.3],
        track_id=12,
        attributes={"pacing_count": 4, "dwell_sec": 8.0}
    )
    events = analyzer.evaluate(1, [det], {}, {})
    assert len(events) == 1
    assert events[0].event_type == "REPEATED_MOVEMENT"
    assert events[0].details["reversals_count"] == 4

# 11. Rapid Movement Analyzer
def test_rapid_movement_analyzer():
    analyzer = RapidMovementAnalyzer(speed_threshold=0.30)
    det = Detection(
        class_name="person",
        confidence=0.9,
        box=[0.2, 0.2, 0.3, 0.3],
        track_id=14,
        attributes={"velocity": (0.35, 0.15)} # speed = sqrt(0.35^2 + 0.15^2) = ~0.38 > 0.30
    )
    events = analyzer.evaluate(1, [det], {}, {})
    assert len(events) == 1
    assert events[0].event_type == "RAPID_MOVEMENT"

# 12. Suspicious Route Analyzer
def test_suspicious_route_analyzer():
    analyzer = SuspiciousRouteAnalyzer()
    det = Detection(class_name="person", confidence=0.9, box=[0.2, 0.2, 0.3, 0.3], track_id=99)
    # Transit Zone 1
    analyzer.evaluate(1, [det], {99: [{"name": "Zone A"}]}, {})
    # Transit Zone 2
    analyzer.evaluate(1, [det], {99: [{"name": "Zone B"}]}, {})
    # Transit Zone 3
    events = analyzer.evaluate(1, [det], {99: [{"name": "Zone C"}]}, {})
    assert len(events) == 1
    assert events[0].event_type == "SUSPICIOUS_ROUTE"

# 13. Incident Intelligence Multi-Event Correlation
def test_incident_intelligence_multi_event_correlation():
    engine = IncidentIntelligenceEngine()
    events = [
        {"event_type": "ZONE_INTRUSION", "rule_id": 1, "details": {"summary": "Entered Restricted Zone A"}},
        {"event_type": "LOITERING", "rule_id": 2, "details": {"summary": "Loitering for 16.5s"}},
        {"event_type": "WRONG_WAY", "rule_id": 3, "details": {"summary": "Wrong-way movement at Exit Gate"}}
    ]

    inc = engine.correlate(
        camera_id=1,
        camera_name="Sector Camera 01",
        track_id=27,
        object_class="person",
        events=events,
        dwell_sec=20.0,
        is_pacing=True,
        is_night=True,
        active_zones=[{"name": "Restricted Sector A", "zone_type": "RESTRICTED"}]
    )

    assert inc is not None
    assert inc["track_id"] == 27
    assert inc["severity"].value in ("CRITICAL", "HIGH")
    assert inc["threat_score"] >= 80.0
    assert len(inc["score_breakdown"]) >= 4
    assert len(inc["timeline"]) == 3
    # Check that explainable timeline is present in summary
    assert "Entered Restricted Zone A" in inc["summary"]
    assert "Loitering for 16.5s" in inc["summary"]

# 14. Rule Evaluator Conditions & Cooldown
def test_rule_evaluator_conditions():
    evaluator = RuleEvaluator()
    rule = Rule(
        id=10,
        name="Loitering Rule",
        event_type=RuleEventType.LOITERING,
        severity=RuleSeverity.HIGH,
        camera_ids_json="[1]",
        conditions_json='{"target_classes": ["person"], "min_dwell_sec": 10.0}',
        schedule_json='{"always": true}',
        cooldown_seconds=30,
        is_active=True
    )

    det_matching = Detection(
        class_name="person",
        confidence=0.85,
        box=[0.2, 0.2, 0.3, 0.3],
        track_id=1,
        attributes={"dwell_sec": 12.0}
    )

    # Should fire
    fired = evaluator.evaluate(1, [rule], det_matching, [], [])
    assert len(fired) == 1
    assert fired[0]["rule_id"] == 10

    # Cooldown should prevent immediate refire
    fired2 = evaluator.evaluate(1, [rule], det_matching, [], [])
    assert len(fired2) == 0
