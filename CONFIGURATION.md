# ARC VISION — Configuration & Environment Reference

All system configurations are managed via environment variables or a `.env` file located in `backend/.env`.

## Core Configuration Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | string | `development` | Environment mode (`development`, `testing`, `production`). |
| `PROJECT_NAME` | string | `ARC VISION - Border AI Surveillance` | Application display name. |
| `VERSION` | string | `1.0.0` | Build version. |
| `API_V1_STR` | string | `/api/v1` | Root API route prefix. |
| `SECRET_KEY` | string | `arc-vision-secure-key` | High-entropy key used for signing JWT tokens. |
| `ALGORITHM` | string | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `1440` (24h) | Access token validity lifetime in minutes. |
| `DATABASE_URL` | string | `sqlite+aiosqlite:///.../arc_vision.db` | SQLAlchemy async connection URI (supports PostgreSQL & SQLite). |
| `DEFAULT_DETECTOR_MODEL` | string | `yolov8n.pt` | Default weight file or ONNX model artifact. |
| `DETECTOR_CONFIDENCE` | float | `0.35` | Global threshold for candidate detection gating. |
| `DEFAULT_INFERENCE_FPS` | int | `15` | Target sampling FPS per active camera worker. |
| `MAX_CAMERAS` | int | `64` | Concurrency limit for active video ingestion workers. |
| `RING_BUFFER_SECONDS` | int | `10` | Duration of pre-incident rolling video buffer. |
| `POST_EVENT_SECONDS` | int | `8` | Duration of post-incident recording window. |

---

## AI & Hardware Worker Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `INFERENCE_BACKEND` | `auto` | Preferred backend (`tensorrt`, `onnx_cuda`, `openvino`, `cpu`). |
| `GPU_DEVICE_IDS` | `0` | Comma-separated GPU ordinal indices for worker pinning (e.g., `0,1,2,3`). |
| `FACE_RECOGNITION_THRESHOLD` | `0.60` | Cosine similarity threshold for confirmed watchlist matches. |
| `FACE_UNCERTAIN_THRESHOLD` | `0.40` | Similarity boundary for triggering UNCERTAIN biometric flags. |
| `ANPR_TEMPORAL_CONSENSUS_FRAMES`| `3` | Minimum consecutive OCR matching frames required before emitting a verified plate event. |
| `NIGHT_MODE_LUMINANCE_THRESHOLD`| `45.0` | Grayscale mean threshold for auto-activating night vision enhancement. |
