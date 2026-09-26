# ARC VISION — Target System Architecture & Engineering Blueprint

## Authoritative System Mission & Problem Statement
- **Problem Statement ID**: SIH26187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance using existing CCTV Infrastructure
- **Target Organization**: Ministry of Home Affairs (MHA) / Sashastra Seema Bal (SSB) / National Border Security Forces
- **Mission Core**: Transform standard, heterogeneous, legacy RTSP/ONVIF CCTV camera infrastructure into a software-defined, GPU-accelerated video intelligence grid without requiring proprietary smart cameras or specialized edge appliances.

---

## 1. End-to-End Pipeline & Abstraction Layering

The ARC VISION platform strictly enforces structural separation across the observation-to-action pipeline:

```
VIDEO STREAM
    │
    ▼
FRAME INGESTION & RING BUFFER
    │
    ▼
ADAPTIVE MOTION GATING & SAMPLING
    │
    ▼
AI INFERENCE FABRIC (Detection, ANPR, Face, Pose, Night Enhancement)
    │
    ▼
MULTI-OBJECT TRACKING ENGINE (ByteTrack/BoT-SORT & Lifecycles)
    │
    ▼
SPATIAL & SCENE INTELLIGENCE (Polygons, Tripwires, Corridors)
    │
    ▼
BEHAVIORAL RULES ENGINE (Loitering, Pacing, Wrong-Way, Crowd, Abandoned)
    │
    ▼
MULTI-SIGNAL INCIDENT CORRELATOR (Weighted Evidence Fusion & Explainability)
    │
    ├─────────────────────────────┬─────────────────────────────┐
    ▼                             ▼                             ▼
CRYPTOGRAPHIC EVIDENCE ENGINE   REAL-TIME ALERT ENGINE      COMMAND CENTER UI
(SHA-256 Hashing, ZIP Manifest) (WebSocket, Push, Webhook)  (Tactical Grid, GIS, Audit)
```

---

## 2. Core Subsystems

### 2.1 Video Ingestion & Camera Worker Architecture
- **Worker Isolation**: Each camera runs an isolated `CameraWorker` / streamer task. A failure, decoder crash, or stream drop in Camera A never blocks or destabilizes other cameras.
- **Protocol Support**: RTSP, RTMP, HTTP, ONVIF discovery, local MP4 virtual test streams.
- **Adaptive Frame Sampling & Gating**: Classical optical flow and frame differencing gate deep model execution during static scenes, reducing compute load while maintaining security sensitivity.
- **Pre/Post Incident Ring Buffer**: Rolling frame buffer maintains pre-incident and post-incident video context for court-admissible evidence compilation.

### 2.2 AI Model Abstraction Layer
- **Model Agnostic Backend**: Clean abstraction over TensorRT, ONNX Runtime (CUDA/DirectML), OpenVINO, and PyTorch CPU fallbacks.
- **Perception Modules**:
  - `DetectorRegistry`: Dynamic dispatch between YOLOv8/v10/v11, ONNX models, and specialized thermal/IR configurations.
  - `FaceIntelligenceEngine`: Independent face detection, quality filtering (sharpness, pose, illumination), and 512-d biometric embedding extraction with cosine similarity gallery matching.
  - `ANPRPipeline`: Multi-stage vehicle localization, license plate crop rectification, OCR text extraction, regex normalization, and multi-frame temporal consensus.
  - `NightVisionEnhancer`: Real-time illumination estimation, dynamic histogram adjustment, and IR-mode profile switching.
  - `CrossCameraReID`: Spatial-temporal topology graph matching, travel-time compatibility bounds, and multi-camera journey reconstruction.

### 2.3 Behavior & Scene Intelligence
Deterministic spatial geometry algorithms evaluate tracks against user-defined zones and fences:
- Point-in-Polygon (Ray-casting)
- Vector Line Segment Intersection (Directional tripwire breaches)
- Pacing & Heading Reversal Detector
- Loitering Duration Accumulator
- Crowd Density & Proximity Analysis
- Abandoned/Stationary Object Tracker

### 2.4 Incident Intelligence & Explainable Severity
Incidents are synthesized from multi-signal evidence chains:
```json
{
  "incident_type": "PERIMETER_INTRUSION",
  "severity": "CRITICAL",
  "threat_score": 95,
  "explainability_chain": [
    "Confirmed PERSON track active for > 5.2s",
    "Breached Restricted Sterile Buffer (Zone #1)",
    "Crossed Directional Fence (Tripwire #2: External -> Internal)",
    "Night surveillance profile active (Low-light condition confirmed)"
  ]
}
```

### 2.5 Cryptographic Evidence Engine
- Generates uncompressed high-resolution snapshots, annotated incident stills, and segmented MP4 video clips.
- Computes SHA-256 hashes of all artifacts at moment of capture.
- Bundles evidence packages with a cryptographically signed JSON manifest verifying chain-of-custody and tamper status.

---

## 3. Distributed Sector Hierarchy

```
COMMAND HQ (Regional Operations)
       │
       ├── SECTOR 01 (Border Sector North)
       │      ├── BOP Alpha (Border Outpost 1) ─── [Cameras 1..16]
       │      └── BOP Bravo (Border Outpost 2) ─── [Cameras 17..32]
       │
       └── SECTOR 02 (Border Sector South)
              ├── BOP Charlie ─── [Cameras 33..48]
              └── BOP Delta   ─── [Cameras 49..64]
```
