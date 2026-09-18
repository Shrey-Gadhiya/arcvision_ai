# ARC VISION: AI-Based Intelligent Video Analytics Platform for Border Surveillance
### Built from Scratch for SIH26187 (MHA / Sashastra Seema Bal)

ARC VISION transforms ordinary legacy, IP, and RTSP CCTV cameras into an autonomous, tactical surveillance grid specifically optimized for remote border perimeters, buffer zones, and checkpoints:

$$\text{RTSP / IP Camera} \longrightarrow \text{Decode} \longrightarrow \text{AI Detection} \longrightarrow \text{Multi-Object Tracking} \longrightarrow \text{Specialized Classifiers (ANPR/Face/Night)} \longrightarrow \text{Zones \& Rules} \longrightarrow \text{Behavior Engine} \longrightarrow \text{Incident Intelligence} \longrightarrow \text{Alerts} \longrightarrow \text{Forensic Evidence (SHA-256)} \longrightarrow \text{Tactical Command Center}$$

---

## 1. Core Architectural Philosophy: $\text{Detection} \neq \text{Event} \neq \text{Incident}$

* **Detection (Raw Telemetry)**: Fast frame-level bounding box inference ($x_1, y_1, x_2, y_2$), target classification (`person`, `car`, `truck`, `motorcycle`), confidence score, and Kalman/ByteTrack trajectory ID.
* **Event (Rule Trigger)**: Atomic condition triggers, e.g. crossing a directional virtual fence line or lingering in a buffer zone.
* **Incident (Correlated Threat Intelligence)**: Multi-factor spatial-temporal threat assessment correlating target identity, trajectory vector, night conditions, dwell time, and zone breaches into a unified threat score ($0-100$).
  * Full lifecycle triage: `NEW` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `RESOLVED` / `FALSE_POSITIVE`.
  * Complete immutable chain of custody with operator notes and tamper-evident SHA-256 cryptographic checksums.

---

## 2. 18 Mission-Control Interfaces

1. **Command Center**: Tactical overview, DEFCON threat gauge, primary live feed spotlight, real-time alert ticker, and one-click incident triage.
2. **Live Grid**: High-density matrix ($1\times1$, $2\times2$, $3\times3$) with real-time AI bounding boxes, polygon zones, directional virtual fences, and FPS telemetry.
3. **Camera Feeds Directory**: Sensor health monitors, RTSP management with credential masking, and worker process control.
4. **Camera Sensor Detail & Zone Canvas**: Interactive canvas to draw custom polygon restricted zones and directional virtual fence tripwires ($A \rightarrow B$ vs $B \rightarrow A$).
5. **Incidents Hub**: Multi-attribute triage hub filtering by status and severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
6. **Incident Detail (Forensic Dossier)**: Synchronized video clip playback, target crops, SHA-256 tamper verification, and immutable operator audit logs.
7. **Forensic Search / Investigation**: Query historical surveillance records by object class, camera, license plate, dwell time, and time ranges.
8. **Threat Timeline**: 24-hour visual density scrubber displaying detection peaks, breach moments, and incident sequences.
9. **ANPR Intelligence**: Real-time vehicle license plate OCR reader, Indian standard plate format regex validation, and suspect/stolen/authorized watchlists.
10. **Face Intelligence**: Facial recognition hit stream, suspect gallery enrollment, and cosine similarity matching.
11. **Zones & Fences**: Central inventory of all active polygon restricted zones and virtual tripwires.
12. **Rules Engine**: Visual condition-action rule builder with schedules and cooldown prevention.
13. **Behavior Parameters**: Fine-tune spatial-temporal sensitivity for loitering, perimeter pacing, stopped vehicles, and crowd clustering.
14. **Alerts Hub**: Real-time push notification center with browser Web Audio tactical alarms.
15. **Evidence Locker**: Tamper-evident repository of recorded MP4 video clips, snapshots, and target crops with SHA-256 bitstream validation.
16. **Tactical Geospatial Map (GIS)**: Border map with camera pins, azimuth heading FOV cones, and active threat blips.
17. **System Health**: Real-time CPU, RAM, disk space, and isolated camera worker thread telemetry.
18. **Audit & Security (RBAC)**: Operator action audit trail and clearance tiers (`ADMIN`, `COMMANDER`, `OPERATOR`, `INVESTIGATOR`, `AUDITOR`).

---

## 3. Quickstart Guide

### Prerequisites
* Python 3.10+ (with PyTorch, OpenCV, Ultralytics, FastAPI, SQLAlchemy)
* Node.js 18+ and npm
* FFmpeg on system PATH

### Step 1: Start Backend
```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
* Backend API documentation available at: `http://localhost:8000/docs`
* On first startup, ARC VISION automatically generates high-definition synthetic border surveillance test streams (`night_perimeter_breach.mp4` and `checkpoint_anpr_vehicle.mp4`), seeds 4 tactical border cameras, configures zones/fences, and sets up test accounts.

### Step 2: Start Frontend
```powershell
cd frontend
npm run dev
```
* Access Tactical Command Center at: `http://localhost:5173`

---

## 4. Default Demonstration Credentials
| Role | Username | Password |
| :--- | :--- | :--- |
| Chief Security Officer (Admin) | `admin` | `admin123` |
| Sector Commander | `commander` | `command123` |
| Surveillance Operator | `operator` | `operator123` |
| Forensic Investigator | `investigator` | `investigate123` |

---

## 5. Modern Frigate-Class NVR / VMS Architecture

ARC VISION integrates the complete practical capability set of a modern **Frigate-class NVR/VMS** while keeping the clean enterprise SOC visual design:

1. **Decoupled Stream Roles**:
   * **Detect Stream**: Dedicated low-resolution feed (e.g. 640x360) for fast YOLOv8 object detection and tracking.
   * **Record Stream**: High-resolution archival feed for lossless forensic recording.
   * **Audio Stream**: Independent audio channel for acoustic/gunshot event detection.
2. **Pre-Inference Motion Detection**:
   * MOG2 background subtraction with contour filtering and polygon motion masks to suppress idle frames and conserve GPU/CPU compute.
3. **Rolling Segment Recording Engine**:
   * Writes continuous, motion-gated, and event-gated 10-second MP4 segments tagged with motion score, detected classes, and SHA-256 tamper-evident integrity hashes.
4. **Best-Frame Representative Snapshots**:
   * Evaluates detection confidence, bounding box pixel area, and Laplacian edge sharpness to save the clearest frame per tracked target.
   * Stores pristine clean frames, tactical annotated frames, and cropped thumbnails.
5. **Multi-Tier Forensic Playback Timeline**:
   * Visual multi-tier scrubber with continuous recording (blue), motion activity ticks (yellow), and incident markers (red).
   * Video controls (play/pause, -10s/+10s, 0.5x–4x speed) and range-based clip export with SHA-256 proof.
6. **Chronological Review Stream**:
   * Target triage feed with instant toggle between Clean, Annotated, and Crop views, and direct jump-to-timeline navigation.
7. **Storage Quotas & Retention Engine**:
   * System disk telemetry, category allocation, and automated per-camera retention enforcement (e.g. 7-day continuous vs. 30-day incident retention).

---

## 6. SIH26187 Deterministic Demonstration Scenarios
1. **Perimeter Intrusion Scenario (CAM-01)**:
   * Intruder emerges in low-light night conditions near northern perimeter fence.
   * Multi-object tracking detects target, tracks velocity vector, and identifies perimeter pacing.
   * Intruder crosses Virtual Fence Alpha into Restricted Zone Sector 4.
   * Incident Intelligence Engine correlates signals and triggers a **CRITICAL BORDER INTRUSION** incident.
   * Evidence Manager records rolling buffer into a verified MP4 clip and high-res snapshot, computing SHA-256 checksums.
   * Operator receives audio alarm and triages incident in Command Center.
2. **Checkpoint ANPR Scenario (CAM-02)**:
   * Vehicle arrives at border barrier lane.
   * Plate localizer and OCR extracts registration string (e.g. `DL01AB1234`).
   * Regex validates format against Indian standard registration specifications.
   * Automated cross-reference against Border Watchlist flags suspect vehicle and alerts checkpoint guard.
3. **Forensic Playback & Review Investigation**:
   * Operator opens **Review Stream** to triage detected targets across cameras.
   * Operator clicks **Timeline** on a target snapshot to jump to the exact recording segment in **Playback Timeline**.
   * Operator marks a time range and exports an evidence clip stamped with cryptographic SHA-256 verification.
