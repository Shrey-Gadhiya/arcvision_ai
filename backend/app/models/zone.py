from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class ZoneType(str, enum.Enum):
    RESTRICTED = "RESTRICTED"       # Absolute no-entry zone (Red)
    BUFFER = "BUFFER"               # Pre-border buffer / warning zone (Orange)
    CHECKPOINT = "CHECKPOINT"       # Entry gate / inspection area (Blue)
    EXCLUSION = "EXCLUSION"         # Ignored area / mask (Gray)

class TripwireDirection(str, enum.Enum):
    BIDIRECTIONAL = "BIDIRECTIONAL" # Breach in either direction
    A_TO_B = "A_TO_B"               # Entry into border territory
    B_TO_A = "B_TO_A"               # Exit from border territory

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    zone_type = Column(Enum(ZoneType), default=ZoneType.RESTRICTED, nullable=False)
    
    # Normalized polygon points JSON: e.g. [{"x": 0.1, "y": 0.2}, {"x": 0.8, "y": 0.2}, ...]
    points_json = Column(Text, nullable=False)
    color_hex = Column(String(10), default="#EF4444") # UI overlay color
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Suspicious behavior parameters
    loitering_time_sec = Column(Integer, default=15)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    camera = relationship("Camera", back_populates="zones")

class Tripwire(Base):
    __tablename__ = "tripwires"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    
    # Normalized coordinates JSON: {"start": {"x": 0.1, "y": 0.5}, "end": {"x": 0.9, "y": 0.5}}
    line_json = Column(Text, nullable=False)
    direction = Column(Enum(TripwireDirection), default=TripwireDirection.A_TO_B, nullable=False)
    color_hex = Column(String(10), default="#F59E0B")
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    camera = relationship("Camera", back_populates="tripwires")
