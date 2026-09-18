from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, ForeignKey
from app.core.database import Base

class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    WEBSOCKET = "WEBSOCKET"
    WEBHOOK = "WEBHOOK"
    MQTT = "MQTT"
    EMAIL = "EMAIL"

class NotificationSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    severity_filter_json = Column(Text, default='["HIGH", "CRITICAL"]', nullable=False)
    camera_ids_json = Column(Text, default="[]", nullable=False) # Empty means all
    event_types_json = Column(Text, default="[]", nullable=False) # Empty means all
    cooldown_seconds = Column(Integer, default=60, nullable=False)
    integration_id = Column(Integer, ForeignKey("integration_configs.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Enum(NotificationSeverity), default=NotificationSeverity.HIGH, nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    dispatched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
