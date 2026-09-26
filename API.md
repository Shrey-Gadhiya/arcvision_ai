# ARC VISION — REST & WebSocket API Specification

Root Endpoint: `http://localhost:8000/api/v1`  
OpenAPI Interactive Docs: `http://localhost:8000/docs`

---

## 1. Authentication & RBAC

- `POST /api/v1/auth/login` — Authenticate operator and receive JWT token.
- `GET /api/v1/auth/me` — Inspect current session user profile & permissions.
- `GET /api/v1/auth/users` — List registered users (ADMIN only).
- `POST /api/v1/auth/users` — Provision new user with role (`ADMIN`, `COMMANDER`, `OPERATOR`, `INVESTIGATOR`, `AUDITOR`).

---

## 2. Cameras & Streaming

- `GET /api/v1/cameras` — Retrieve all registered CCTV cameras with online/degraded status.
- `POST /api/v1/cameras` — Register a new RTSP/ONVIF camera.
- `GET /api/v1/cameras/{id}` — Fetch detailed telemetry, assigned AI profile, and stats.
- `PUT /api/v1/cameras/{id}` — Update camera configuration, stream URL, or target FPS.
- `DELETE /api/v1/cameras/{id}` — Deregister camera and terminate worker process.
- `GET /api/v1/streams/{id}/live` — Live MJPEG stream endpoint for real-time dashboard display.

---

## 3. Spatial Zones & Tripwires

- `GET /api/v1/zones` — Query all active restricted polygons and directional tripwires.
- `POST /api/v1/zones` — Create a virtual fence, sterile zone, or entry corridor.
- `DELETE /api/v1/zones/{id}` — Delete a zone.

---

## 4. Behavioral Rules & Incidents

- `GET /api/v1/rules` — Retrieve behavioral trigger rules (Loitering, Pacing, Intrusion, Wrong-Way).
- `POST /api/v1/rules` — Define new deterministic rule criteria and severity level.
- `GET /api/v1/incidents` — Search and filter correlated security incidents.
- `GET /api/v1/incidents/{id}` — Inspect detailed incident evidence chain and explainability manifest.
- `PATCH /api/v1/incidents/{id}/status` — Update incident status (`ACKNOWLEDGED`, `INVESTIGATING`, `ESCALATED`, `RESOLVED`, `FALSE_POSITIVE`).

---

## 5. Cryptographic Evidence & Forensics

- `GET /api/v1/evidence` — List secured evidence items, SHA-256 hashes, and video clips.
- `GET /api/v1/evidence/{id}/verify` — Perform real-time cryptographic SHA-256 hash audit on disk file.
- `POST /api/v1/evidence/export-package` — Export a court-admissible signed ZIP evidence package with metadata manifest.
- `POST /api/v1/evidence/verify-package` — Verify the integrity of an exported evidence bundle.

---

## 6. ANPR & Face Intelligence

- `GET /api/v1/anpr/records` — Query captured vehicle license plates with temporal consensus scores.
- `GET /api/v1/anpr/watchlist` — View vehicle security watchlists (`AUTHORIZED`, `SUSPECT`, `STOLEN`).
- `POST /api/v1/anpr/watchlist` — Enlist license plate for instant intrusion alerting.
- `GET /api/v1/face/records` — Query face detections with quality scores and biometric matching status.
- `GET /api/v1/face/identities` — View enrolled facial recognition watchlist gallery.
- `POST /api/v1/face/identities` — Enroll subject photo for automated biometric detection.

---

## 7. Real-Time Telemetry WebSockets

- `WS /api/v1/ws` or `/ws` — Bidirectional real-time stream for instant alert dispatches, live track updates, and system health status.
