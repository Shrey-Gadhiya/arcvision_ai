import pytest
from app.core.security import mask_rtsp_url, mask_secret
from app.models.user import UserRole
from app.models.integration import IntegrationType, IntegrationStatus
from app.models.notification import NotificationSeverity, NotificationChannel

def test_mask_rtsp_url():
    raw_url = "rtsp://admin:superSecretPass123@192.168.1.55:554/h264Preview_01_main"
    masked = mask_rtsp_url(raw_url)
    assert "superSecretPass123" not in masked
    assert masked == "rtsp://admin:******@192.168.1.55:554/h264Preview_01_main"

def test_mask_rtsp_url_no_credentials():
    raw_url = "rtsp://192.168.1.55:554/live"
    assert mask_rtsp_url(raw_url) == raw_url

def test_mask_secret():
    secret = "sk_prod_998877665544332211"
    masked = mask_secret(secret)
    assert "9988776655" not in masked
    assert masked.startswith("sk_")
    assert masked.endswith("211")

def test_user_roles_coverage():
    roles = [r.value for r in UserRole]
    assert "ADMIN" in roles
    assert "COMMANDER" in roles
    assert "OPERATOR" in roles
    assert "INVESTIGATOR" in roles
    assert "VIEWER" in roles
