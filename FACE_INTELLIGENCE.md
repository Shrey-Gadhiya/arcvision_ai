# ARC VISION — Face Intelligence & Biometric Subsystem

## 1. Controlled Face Processing Pipeline

Biometric identity matching is implemented as an audited intelligence layer:

```
Frame Capture ──► Face Detection (ResNet-10 DNN)
                        │
                        ▼
                [ Quality Filter ]
                  ├── Sharpness (Laplacian Var >= 100)
                  ├── Pixel Dimension (>= 64x64 px)
                  └── Illumination & Head Pose
                        │ (Passes Quality)
                        ▼
                [ 512-d Embedding Extraction ]
                        │
                        ▼
                [ Cosine Gallery Search ]
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
    [ KNOWN ]     [ UNCERTAIN ]    [ UNKNOWN ]    [ LOW_QUALITY ]
  (Sim >= 0.60)   (0.40 <= Sim < 0.60) (Sim < 0.40)  (Failed Filter)
```

---

## 2. Watchlist Dispatch & Governance
- **Categories**: `WATCH`, `SUSPECT`, `AUTHORIZED`, `PERSON_OF_INTEREST`.
- **Alert Dispatch**: Confirmed matches trigger instant high-severity incident notifications to the tactical command center with associated enrolled photo reference.
- **Privacy Controls**: Facial embeddings are stored as mathematical feature vectors; raw unredacted biometrics are protected under role-based authorization controls.
