# ARC VISION — Person Appearance Re-ID & Cross-Camera Intelligence

## 1. Appearance Embedding & Topological Association

Cross-camera identity tracking correlates targets across non-overlapping camera FOVs by fusing visual appearance embeddings with a physical topology graph:

```
Camera A (Entry BOP)                           Camera B (Perimeter Checkpoint)
Track ID #102                                 Track ID #204
Appearance Vector A (512-d)                   Appearance Vector B (512-d)
Timestamp: 14:02:10                           Timestamp: 14:02:45 (Elapsed: 35s)
          │                                             │
          └──────────────────────┬──────────────────────┘
                                 ▼
                     [ Cross-Camera Correlator ]
                                 │
     ├── 1. Appearance Match: Cosine Similarity(A, B) = 0.88
     ├── 2. Spatial-Temporal Bounds: Travel Time (35s) within [15s, 60s]
     └── 3. Graph Transition Probability: Valid Forward Path (0.95)
                                 │
                                 ▼
           Match Status: CONFIRMED GLOBAL IDENTITY (GLOBAL-P-00102)
```

---

## 2. Match Status Classifications
- `MATCH`: Cosine similarity $\ge 0.85$ and travel time strictly within topological bounds.
- `PROBABLE_MATCH`: Similarity $0.70 - 0.84$ within expected time window.
- `UNCERTAIN`: Conflicting spatial constraints or marginal similarity ($0.50 - 0.69$).
- `NO_MATCH`: Low similarity or physically impossible travel time (e.g. speed $> 120\text{ km/h}$ on foot).
