import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.api.v1 import (
    auth,
    cameras,
    streams,
    zones,
    rules,
    incidents,
    anpr,
    face,
    evidence,
    investigation,
    map as map_router,
    health,
    audit,
    demo,
    ws,
    recordings,
    snapshots,
    integrations,
    notifications,
    models,
    analytics,
    cross_camera,
    ptz
)
from app.services.stream_manager import stream_manager
from app.models.camera import Camera
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("arc_vision.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("Initializing ARC VISION Tactical Surveillance Core...")
    await init_db()

    # Seed or verify default RBAC user accounts
    async with AsyncSessionLocal() as session:
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        users_to_seed = [
            ("admin", "admin@ssb.gov.in", "admin123", "Administrator", UserRole.ADMIN),
            ("commander", "commander@ssb.gov.in", "command123", "Sector Commander", UserRole.COMMANDER),
            ("operator", "operator@ssb.gov.in", "operator123", "Surveillance Operator", UserRole.OPERATOR),
            ("investigator", "investigator@ssb.gov.in", "investigate123", "Forensic Investigator", UserRole.INVESTIGATOR),
        ]
        for uname, email, pwd, fname, role in users_to_seed:
            existing = await session.execute(select(User).where(User.username == uname))
            u = existing.scalars().first()
            if not u:
                session.add(User(
                    username=uname,
                    email=email,
                    hashed_password=get_password_hash(pwd),
                    full_name=fname,
                    role=role,
                    is_active=True
                ))
            else:
                u.hashed_password = get_password_hash(pwd)
                u.is_active = True
        await session.commit()
        logger.info("RBAC user accounts verified and ready.")

    # Reconnect any cameras that already exist in the database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Camera))
        cams = result.scalars().all()
        if not cams:
            logger.info("Clean system — no cameras configured. Add cameras via the UI.")
        else:
            for c in cams:
                if c.is_active:
                    stream_manager.start_streamer(
                        camera_id=c.id,
                        camera_name=c.name,
                        stream_url=c.rtsp_url,
                        stream_type=c.stream_type.value,
                        target_fps=c.target_fps,
                        is_night_mode=c.night_mode_enabled
                    )

    logger.info("ARC VISION Core online and operational.")
    yield

    # --- SHUTDOWN ---
    logger.info("Shutting down camera stream workers...")
    for cam_id in list(stream_manager.get_all_streamers().keys()):
        stream_manager.stop_streamer(cam_id)
    logger.info("ARC VISION Core gracefully stopped.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Based Intelligent Video Analytics Platform for Border Surveillance using existing CCTV Infrastructure (SIH26187 / MHA / SSB)",
    lifespan=lifespan
)

# CORS Configuration for local & multi-device LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static media mounts for forensic evidence, recordings, snapshots, and uploads
import os
os.makedirs(str(settings.SNAPSHOTS_DIR), exist_ok=True)
os.makedirs(os.path.join(str(settings.SNAPSHOTS_DIR), "anpr"), exist_ok=True)
os.makedirs(os.path.join(str(settings.SNAPSHOTS_DIR), "faces"), exist_ok=True)
os.makedirs(str(settings.UPLOADS_DIR), exist_ok=True)
os.makedirs(str(settings.EVIDENCE_DIR), exist_ok=True)
os.makedirs(str(settings.RECORDINGS_DIR), exist_ok=True)

# Mount both /static/* and standard root paths for 100% media URL compatibility
app.mount("/static/snapshots", StaticFiles(directory=str(settings.SNAPSHOTS_DIR)), name="static_snapshots")
app.mount("/static/uploads", StaticFiles(directory=str(settings.UPLOADS_DIR)), name="static_uploads")
app.mount("/static/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="static_evidence")
app.mount("/static/recordings", StaticFiles(directory=str(settings.RECORDINGS_DIR)), name="static_recordings")
app.mount("/static", StaticFiles(directory="data"), name="static_root")

app.mount("/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")
app.mount("/recordings", StaticFiles(directory=str(settings.RECORDINGS_DIR)), name="recordings")
app.mount("/snapshots", StaticFiles(directory=str(settings.SNAPSHOTS_DIR)), name="snapshots")
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOADS_DIR)), name="uploads")

# Include Routers
api_v1 = settings.API_V1_STR
app.include_router(auth.router, prefix=api_v1)
app.include_router(cameras.router, prefix=api_v1)
app.include_router(streams.router, prefix=api_v1)
app.include_router(recordings.router, prefix=api_v1)
app.include_router(snapshots.router, prefix=api_v1)
app.include_router(zones.router, prefix=api_v1)
app.include_router(rules.router, prefix=api_v1)
app.include_router(incidents.router, prefix=api_v1)
app.include_router(anpr.router, prefix=api_v1)
app.include_router(face.router, prefix=api_v1)
app.include_router(evidence.router, prefix=api_v1)
app.include_router(investigation.router, prefix=api_v1)
app.include_router(map_router.router, prefix=api_v1)
app.include_router(health.router, prefix=api_v1)
app.include_router(audit.router, prefix=api_v1)
app.include_router(integrations.router, prefix=api_v1)
app.include_router(notifications.router, prefix=api_v1)
app.include_router(models.router, prefix=api_v1)
app.include_router(analytics.router, prefix=api_v1)
app.include_router(cross_camera.router, prefix=api_v1)
app.include_router(ptz.router, prefix=api_v1)
app.include_router(demo.router, prefix=api_v1)
app.include_router(ws.router, prefix=api_v1)
app.include_router(ws.router) # also mount /ws at root for convenience

@app.get("/")
async def root():
    return {
        "system": "ARC VISION Tactical AI Surveillance Platform",
        "mission": "SIH26187: Border Surveillance using existing CCTV Infrastructure (MHA/SSB)",
        "status": "OPERATIONAL",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }
