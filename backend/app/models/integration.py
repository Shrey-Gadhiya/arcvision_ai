from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from app.core.database import Base

class IntegrationType(str, enum.Enum):
    WEBHOOK = "WEBHOOK"
    MQTT = "MQTT"
    REST_CALLBACK = "REST_CALLBACK"
    EMAIL = "EMAIL"

class IntegrationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"

class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    integration_type = Column(Enum(IntegrationType), nullable=False)
    endpoint_url = Column(String(500), nullable=True) # Webhook URL or MQTT Broker Host
    port = Column(Integer, nullable=True) # e.g. 1883 / 8883
    topic = Column(String(255), nullable=True) # e.g. arc_vision/events
    auth_secret = Column(String(255), nullable=True) # Token / Password (stored encrypted/masked on read)
    headers_json = Column(Text, default="{}", nullable=False)
    qos = Column(Integer, default=1, nullable=False)
    tls_enabled = Column(Boolean, default=False, nullable=False)
    retry_count = Column(Integer, default=3, nullable=False)
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.INACTIVE, nullable=False)
    last_dispatched_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
