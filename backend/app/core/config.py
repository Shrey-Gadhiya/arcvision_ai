from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ARC VISION - Border AI Surveillance"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "arc-vision-sih26187-border-surveillance-secure-key-9988"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    EVIDENCE_DIR: Path = DATA_DIR / "evidence"
    DEMO_DIR: Path = DATA_DIR / "demos"
    RECORDINGS_DIR: Path = DATA_DIR / "recordings"
    SNAPSHOTS_DIR: Path = DATA_DIR / "snapshots"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR.as_posix()}/arc_vision.db"
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    DEFAULT_DETECTOR_MODEL: str = "yolov8n.pt"
    DETECTOR_CONFIDENCE: float = 0.35
    DEFAULT_INFERENCE_FPS: int = 15
    MAX_CAMERAS: int = 64
    
    # Ring buffer configuration for pre/post event recording
    RING_BUFFER_SECONDS: int = 10
    POST_EVENT_SECONDS: int = 8
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.DEMO_DIR.mkdir(parents=True, exist_ok=True)
settings.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
settings.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
