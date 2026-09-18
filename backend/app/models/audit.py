import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base

class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"
    ACCESS = "ACCESS"
    SEARCH = "SEARCH"
    LOGIN = "LOGIN"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, index=True)
    user_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True) # LOGIN, ACKNOWLEDGE_INCIDENT, MODIFY_ZONE, EXPORT_EVIDENCE, etc.
    resource_type = Column(String(50), nullable=False) # CAMERA, INCIDENT, RULE, ZONE, EVIDENCE, USER
    resource_id = Column(String(50), nullable=True)
    details_json = Column(Text, default="{}")
    ip_address = Column(String(50), default="127.0.0.1")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
