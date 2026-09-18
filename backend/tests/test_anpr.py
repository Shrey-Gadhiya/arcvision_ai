import pytest
from app.services.ai.anpr_engine import clean_plate_text, validate_plate

def test_clean_plate_text():
    raw = "DL 01-AB_1234"
    assert clean_plate_text(raw) == "DL01AB1234"

def test_validate_plate_standard_indian():
    is_valid, conf = validate_plate("DL01AB1234")
    assert is_valid is True
    assert conf >= 0.9

    is_valid2, conf2 = validate_plate("JK02BB7711")
    assert is_valid2 is True
    assert conf2 >= 0.9

    is_valid3, conf3 = validate_plate("INVALID")
    assert conf3 <= 0.7
