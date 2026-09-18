import pytest
from app.services.analytics.zone_engine import is_point_in_polygon, do_lines_intersect, get_crossing_direction, zone_engine

def test_point_in_polygon():
    # Square from (0.2, 0.2) to (0.8, 0.8)
    poly = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]

    # Point inside
    assert is_point_in_polygon(0.5, 0.5, poly) is True
    assert is_point_in_polygon(0.3, 0.7, poly) is True

    # Point outside
    assert is_point_in_polygon(0.1, 0.5, poly) is False
    assert is_point_in_polygon(0.9, 0.9, poly) is False
    assert is_point_in_polygon(0.5, 0.1, poly) is False

def test_line_intersection():
    # Horizontal line from (0.1, 0.5) to (0.9, 0.5)
    L1_start = (0.1, 0.5)
    L1_end = (0.9, 0.5)

    # Vertical trajectory cutting from top to bottom (0.5, 0.3) -> (0.5, 0.7)
    T1_prev = (0.5, 0.3)
    T1_curr = (0.5, 0.7)
    assert do_lines_intersect(T1_prev, T1_curr, L1_start, L1_end) is True

    # Trajectory that does not cross (0.5, 0.1) -> (0.5, 0.3)
    T2_prev = (0.5, 0.1)
    T2_curr = (0.5, 0.3)
    assert do_lines_intersect(T2_prev, T2_curr, L1_start, L1_end) is False

def test_tripwire_crossing_direction():
    # Wire from Left (0.1, 0.5) to Right (0.9, 0.5)
    line_start = (0.1, 0.5)
    line_end = (0.9, 0.5)

    # Moving top (0.5, 0.2) to bottom (0.5, 0.8)
    p_prev = (0.5, 0.2)
    p_curr = (0.5, 0.8)
    direction = get_crossing_direction(p_prev, p_curr, line_start, line_end)
    assert direction in ["A_TO_B", "B_TO_A"]
