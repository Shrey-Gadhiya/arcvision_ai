from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class PTZStatusEnum(str, enum.Enum):
    CONNECTED = "CONNECTED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"

class PTZModeEnum(str, enum.Enum):
    CONTINUOUS = "CONTINUOUS"
    RELATIVE = "RELATIVE"
    ABSOLUTE = "ABSOLUTE"

class PTZPreset(Base):
    __tablename__ = "ptz_presets"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    preset_token = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    
    pan = Column(Float, default=0.0)
    tilt = Column(Float, default=0.0)
    zoom = Column(Float, default=1.0)
    
    is_home = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PTZLog(Base):
    __tablename__ = "ptz_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False) # MOVE, STOP, GOTO_PRESET, SET_PRESET, HOME
    parameters_json = Column(Text, default="{}")
    status = Column(Enum(PTZStatusEnum), default=PTZStatusEnum.CONNECTED)
    error_message = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
