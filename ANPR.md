# ARC VISION — Automated Number Plate Recognition (ANPR / ALPR)

## 1. Multi-Stage Pipeline & Temporal Consensus

The ANPR engine ensures high read accuracy through multi-frame temporal consensus:

```
Vehicle Detection (YOLO)
          │
          ▼
Plate Localization & Crop
          │
          ▼
Perspective Rectification (Homography)
          │
          ▼
Contrast Enhancement & Binarization
          │
          ▼
OCR Text Extraction (EasyOCR / CRNN)
          │
          ▼
Character Normalization & MoRTH Regex Validation (e.g., DL01AB1234)
          │
          ▼
Temporal Consensus Engine (Minimum 3 identical matching frames)
          │
          ▼
Watchlist Cross-Check (AUTHORIZED / SUSPECT / STOLEN)
          │
          ▼
Security Event & Incident Dispatch
```

---

## 2. Watchlist Triggering & Telemetry
- **Watchlist Types**: `AUTHORIZED` (Green Pass), `SUSPECT` (Orange Alert), `STOLEN` (Red Critical Intrusion).
- **Metadata Captured**: Normalized Plate Text, Raw OCR, Frame Consensus Count, Confidence Score, Vehicle Track ID, High-Resolution Plate Crop, Timestamp, and Camera ID.
