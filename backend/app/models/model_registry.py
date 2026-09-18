from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Float
from app.core.database import Base

class AIModelTask(str, enum.Enum):
    DETECTION = "DETECTION"
    TRACKING = "TRACKING"
    FACE_DETECTION = "FACE_DETECTION"
    FACE_RECOGNITION = "FACE_RECOGNITION"
    ANPR_DETECTION = "ANPR_DETECTION"
    ANPR_OCR = "ANPR_OCR"
    POSE_ESTIMATION = "POSE_ESTIMATION"
    FALL_DETECTION = "FALL_DETECTION"
    ACTION_RECOGNITION = "ACTION_RECOGNITION"
    FIRE_SMOKE_DETECTION = "FIRE_SMOKE_DETECTION"
    WEAPON_DETECTION = "WEAPON_DETECTION"
    CROWD_ANALYSIS = "CROWD_ANALYSIS"
    ATTRIBUTE_ANALYSIS = "ATTRIBUTE_ANALYSIS"
    PERSON_REID = "PERSON_REID"
    VEHICLE_REID = "VEHICLE_REID"
    BEHAVIOR = "BEHAVIOR"
    NIGHT_ENHANCEMENT = "NIGHT_ENHANCEMENT"

class AIModelStatus(str, enum.Enum):
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    STANDBY = "STANDBY"
    MODEL_REQUIRED = "MODEL_REQUIRED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"

class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    version = Column(String(50), default="1.0.0", nullable=False)
    task = Column(Enum(AIModelTask), nullable=False)
    provider = Column(String(100), default="Ultralytics / ONNX", nullable=False) # e.g. YOLO, ONNX Runtime, OpenVINO
    model_path = Column(String(500), nullable=False)
    format = Column(String(50), default="PyTorch/ONNX", nullable=False) # pt, onnx, engine, xml
    input_resolution = Column(String(50), default="640x640", nullable=False)
    classes_json = Column(Text, default="[]", nullable=False)
    device = Column(String(50), default="CPU", nullable=False) # CPU, CUDA:0, OpenVINO
    status = Column(Enum(AIModelStatus), default=AIModelStatus.STANDBY, nullable=False)
    inference_latency_ms = Column(Float, default=0.0, nullable=False)
    inference_fps = Column(Float, default=0.0, nullable=False)
    memory_mb = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
