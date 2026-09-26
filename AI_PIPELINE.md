# ARC VISION — AI/ML Perception & Analytics Pipeline

## 1. Multi-Stage Inference Fabric

```
Frame Capture (RTSP / Video)
          │
          ▼
   [ Motion Gating ]  ──(Static Frame)──► [ Low Power Skip ]
          │ (Motion Detected)
          ▼
   [ Illumination Analysis ] ──(Low Light < 45 LUX)──► [ CLAHE / IR Enhancement ]
          │
          ▼
   [ Primary Object Detection ] (YOLO / ONNX / OpenVINO / TensorRT)
     - Classes: person, bicycle, car, motorcycle, bus, truck, boat, backpack
          │
          ▼
   [ Multi-Object Tracking (MOT) ] (ByteTrack / BoT-SORT)
     - ID Association, Trajectory Vector, Velocity (dx/dt, dy/dt), Heading
          │
    ┌─────┴───────────────────────────────┬──────────────────────────────┐
    ▼                                     ▼                              ▼
[ Face Intelligence ]              [ ANPR / ALPR ]              [ Spatial & Behavior ]
- Face Localization               - Vehicle ROI Isolation       - Point-in-Polygon Check
- Quality Filtering               - Plate Rectification         - Directional Tripwire Breach
- Biometric Embedding (512-d)     - OCR Text Extraction         - Loitering Duration Engine
- Cosine Similarity Match         - Temporal Consensus (3+ f)   - Perimeter Pacing Detector
- Watchlist Trigger               - Watchlist Lookup            - Crowd Density Aggregator
```

---

## 2. Multi-Signal Incident Correlation & Explainability

ARC VISION never generates alarms directly from isolated detector outputs. Instead, events are aggregated through an explainable multi-signal correlation matrix:

$$\text{Threat Score} = \sum w_i \times E_i$$

Where:
- $E_{\text{class}}$: Target classification confidence (e.g. Person = 1.0)
- $E_{\text{zone}}$: Zone sensitivity weight (Restricted = 1.5, Sterile Buffer = 2.0)
- $E_{\text{direction}}$: Vector orientation towards perimeter (Crossing towards internal = 1.8)
- $E_{\text{time}}$: Temporal restriction factor (Night hours 22:00–05:00 = 1.5)
- $E_{\text{persistence}}$: Minimum track confirmation duration ($t > 3.0\text{s} \implies 1.2$)

---

## 3. False-Positive Mitigation Gating
1. **Confidence Hysteresis**: Detections must exceed an entry threshold ($0.45$) to initiate a track and remain above $0.25$ to maintain track state.
2. **Track Confirmation Floor**: Tracks are marked `TENTATIVE` and do not fire security alerts until verified across $\ge 5$ consecutive frames.
3. **Temporal OCR Consensus**: A license plate must produce identical normalized alphanumeric characters across $\ge 3$ consecutive frames before confirming identity.
4. **Biometric Quality Filter**: Facial crops failing Laplacian variance sharpness ($\text{Var} < 100$) or minimum pixel dimension ($< 64\times 64$) are quarantined as `UNCERTAIN` rather than false matches.
