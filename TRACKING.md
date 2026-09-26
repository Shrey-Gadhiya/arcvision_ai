# ARC VISION — Multi-Object Tracking (MOT) & Lifecycle Engine

## 1. Track State Machine & Lifecycle

ARC VISION implements a deterministic state machine to eliminate false positives from momentary transient detections:

```
[ New Detection ] ──(Initial Frame)──► [ TENTATIVE ] (Floor: 5 consecutive frames)
                                              │
                                   (Confirmed Detection)
                                              ▼
                                       [ CONFIRMED ] ──(Emits Security Events)
                                              │
                                     (Missed Detection)
                                              ▼
                                       [ OCCLUDED ]
                                              │
                                    (Exceeded Max Misses)
                                              ▼
                                         [ LOST ]
                                              │
                                    (Age Timeout > 30s)
                                              ▼
                                      [ TERMINATED ]
```

---

## 2. Track Attributes & Kinematic Telemetry

Every active track maintains real-time spatial and temporal descriptors:
- **Spatial Coordinates**: Normalized bounding box $[x_1, y_1, x_2, y_2]$ and centroid $(c_x, c_y)$.
- **Trajectory Vector**: Historical sequence of coordinates $[(x_t, y_t, t_0), \dots, (x_n, y_n, t_n)]$.
- **Velocity**: Instantaneous differential $(dx/dt, dy/dt)$ in normalized units/second.
- **Heading & Direction Reversals**: Angular orientation and count of $180^\circ$ direction changes for perimeter pacing detection.
- **Appearance Embedding**: Feature vectors for cross-camera re-identification.
