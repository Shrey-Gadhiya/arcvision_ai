from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False, "timeout": 30.0} if "sqlite" in settings.DATABASE_URL else {}
)

# Enable SQLite pragmas for WAL mode and foreign key enforcement on every new connection
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def migrate_sqlite(connection):
            try:
                # 1. cameras table migration
                res = connection.execute(text("PRAGMA table_info(cameras)")).fetchall()
                existing_cols = [row[1] for row in res]
                new_columns = [
                    ("detect_stream_url", "VARCHAR(500)"),
                    ("record_stream_url", "VARCHAR(500)"),
                    ("audio_stream_url", "VARCHAR(500)"),
                    ("recording_mode", "VARCHAR(20) DEFAULT 'CONTINUOUS'"),
                    ("retention_days", "INTEGER DEFAULT 7"),
                    ("retention_events_days", "INTEGER DEFAULT 30"),
                    ("pre_event_seconds", "INTEGER DEFAULT 5"),
                    ("post_event_seconds", "INTEGER DEFAULT 15"),
                    ("active_profile", "VARCHAR(50) DEFAULT 'NORMAL'"),
                    ("motion_detection_enabled", "BOOLEAN DEFAULT 1"),
                    ("anpr_enabled", "BOOLEAN DEFAULT 1"),
                    ("motion_threshold", "INTEGER DEFAULT 25"),
                    ("motion_min_area", "INTEGER DEFAULT 500")
                ]
                for col_name, col_type in new_columns:
                    if col_name not in existing_cols:
                        connection.execute(text(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_type}"))

                # 1b. Phase K: ONVIF/PTZ/geospatial camera columns
                ptz_columns = [
                    ("ptz_enabled", "BOOLEAN DEFAULT 0"),
                    ("onvif_host", "VARCHAR(100)"),
                    ("onvif_port", "INTEGER DEFAULT 80"),
                    ("onvif_username", "VARCHAR(100)"),
                    ("onvif_password_encrypted", "VARCHAR(255)"),
                    ("onvif_profile_token", "VARCHAR(100)"),
                    ("altitude_m", "FLOAT DEFAULT 120.0"),
                    ("heading_deg", "FLOAT DEFAULT 45.0"),
                    ("fov_angle", "FLOAT DEFAULT 78.0"),
                    ("range_meters", "FLOAT DEFAULT 150.0"),
                ]
                for col_name, col_type in ptz_columns:
                    if col_name not in existing_cols:
                        connection.execute(text(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_type}"))

                # 2. incidents table migration
                inc_res = connection.execute(text("PRAGMA table_info(incidents)")).fetchall()
                inc_cols = [row[1] for row in inc_res]
                inc_new = [
                    ("assigned_to", "VARCHAR(100)"),
                    ("assigned_at", "DATETIME"),
                    ("triaged_at", "DATETIME"),
                    ("triaged_by", "VARCHAR(50)"),
                    ("acknowledged_at", "DATETIME"),
                    ("acknowledged_by", "VARCHAR(50)"),
                    ("resolved_at", "DATETIME"),
                    ("resolved_by", "VARCHAR(50)"),
                    ("closed_at", "DATETIME"),
                    ("closed_by", "VARCHAR(50)"),
                    ("resolution_reason", "VARCHAR(100)"),
                    ("resolution_notes", "TEXT"),
                    ("transition_history_json", "TEXT DEFAULT '[]'"),
                    ("operator_notes_json", "TEXT DEFAULT '[]'")
                ]
                for col_name, col_type in inc_new:
                    if col_name not in inc_cols:
                        connection.execute(text(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_type}"))

                # 3. anpr_watchlists table migration
                w_res = connection.execute(text("PRAGMA table_info(anpr_watchlists)")).fetchall()
                w_cols = [row[1] for row in w_res]
                w_new = [
                    ("priority", "VARCHAR(20) DEFAULT 'HIGH'"),
                    ("updated_at", "DATETIME")
                ]
                for col_name, col_type in w_new:
                    if col_name not in w_cols:
                        connection.execute(text(f"ALTER TABLE anpr_watchlists ADD COLUMN {col_name} {col_type}"))

                # 3. anpr_records table migration
                r_res = connection.execute(text("PRAGMA table_info(anpr_records)")).fetchall()
                r_cols = [row[1] for row in r_res]
                r_new = [
                    ("track_id", "INTEGER DEFAULT -1"),
                    ("raw_text", "VARCHAR(50)"),
                    ("validation_status", "VARCHAR(20) DEFAULT 'VALID'"),
                    ("validation_format", "VARCHAR(50) DEFAULT 'INDIAN_STANDARD'"),
                    ("diagnostics", "VARCHAR(255)"),
                    ("vehicle_color", "VARCHAR(50)"),
                    ("vehicle_make", "VARCHAR(50)"),
                    ("vehicle_model", "VARCHAR(50)"),
                    ("is_stationary", "BOOLEAN DEFAULT 0"),
                    ("dwell_duration_sec", "FLOAT DEFAULT 0.0"),
                    ("watchlist_priority", "VARCHAR(50)"),
                    ("vehicle_crop_path", "VARCHAR(500)"),
                    ("evidence_id", "INTEGER"),
                    ("recording_segment_id", "INTEGER")
                ]
                for col_name, col_type in r_new:
                    if col_name not in r_cols:
                        connection.execute(text(f"ALTER TABLE anpr_records ADD COLUMN {col_name} {col_type}"))

                # 5. face_records table migration
                fr_res = connection.execute(text("PRAGMA table_info(face_records)")).fetchall()
                fr_cols = [row[1] for row in fr_res]
                fr_new = [
                    ("track_id", "INTEGER DEFAULT -1"),
                    ("unique_person_id", "VARCHAR(50)"),
                    ("match_status", "VARCHAR(20) DEFAULT 'UNKNOWN'"),
                    ("identity_id", "INTEGER"),
                    ("bbox_json", "VARCHAR(200)"),
                    ("landmarks_json", "VARCHAR(500)"),
                    ("quality_score", "FLOAT DEFAULT 0.0"),
                    ("watchlist_category", "VARCHAR(50)"),
                    ("watchlist_priority", "VARCHAR(50)"),
                    ("full_frame_path", "VARCHAR(500)"),
                    ("evidence_id", "INTEGER"),
                    ("recording_segment_id", "INTEGER")
                ]
                for col_name, col_type in fr_new:
                    if col_name not in fr_cols:
                        connection.execute(text(f"ALTER TABLE face_records ADD COLUMN {col_name} {col_type}"))

                # 6. face_identities table migration (if upgraded from face_watchlists)
                fi_res = connection.execute(text("PRAGMA table_info(face_identities)")).fetchall()
                fi_cols = [row[1] for row in fi_res]
                fi_new = [
                    ("external_id", "VARCHAR(50)"),
                    ("unique_person_id", "VARCHAR(50)"),
                    ("priority", "VARCHAR(20) DEFAULT 'HIGH'"),
                    ("quality_score", "FLOAT DEFAULT 0.85"),
                    ("created_by", "VARCHAR(50) DEFAULT 'SYSTEM'"),
                    ("updated_at", "DATETIME")
                ]
                for col_name, col_type in fi_new:
                    if col_name not in fi_cols:
                        connection.execute(text(f"ALTER TABLE face_identities ADD COLUMN {col_name} {col_type}"))

                # 7. investigation_cases table migration
                ic_res = connection.execute(text("PRAGMA table_info(investigation_cases)")).fetchall()
                ic_cols = [row[1] for row in ic_res]
                ic_new = [
                    ("hypothesis", "TEXT"),
                    ("tags_json", "TEXT DEFAULT '[]'"),
                    ("lead_investigator", "VARCHAR(100) DEFAULT 'Lead Investigator'"),
                    ("closed_at", "DATETIME")
                ]
                for col_name, col_type in ic_new:
                    if col_name not in ic_cols and ic_cols:
                        connection.execute(text(f"ALTER TABLE investigation_cases ADD COLUMN {col_name} {col_type}"))

                # 8. case_findings table migration
                cf_res = connection.execute(text("PRAGMA table_info(case_findings)")).fetchall()
                cf_cols = [row[1] for row in cf_res]
                cf_new = [
                    ("metadata_json", "TEXT DEFAULT '{}'"),
                    ("thumbnail_url", "VARCHAR(500)"),
                    ("notes", "TEXT")
                ]
                for col_name, col_type in cf_new:
                    if col_name not in cf_cols and cf_cols:
                        connection.execute(text(f"ALTER TABLE case_findings ADD COLUMN {col_name} {col_type}"))
            except Exception as e:
                pass

        await conn.run_sync(migrate_sqlite)

