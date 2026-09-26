# ARC VISION — Operational Runbook & Tactical Procedures

## 1. Daily Shift Operations & Triage Workflow

```
1. Operator logs into Tactical Command Center (http://localhost:5173).
2. Monitor Live Camera Grid (1x1, 2x2, 3x3, or 4x4 matrix).
3. Real-Time Alert arrives via WebSocket banner with audio alert tone.
4. Click incident banner to navigate directly to Incident Investigation page.
5. Review Explainable AI Evidence Chain:
   - Target trajectory & velocity vector
   - Breached zone / fence boundaries
   - Temporal conditions & night profile
6. Operator Actions:
   - ACKNOWLEDGE: Mark alert as seen.
   - ESCALATE: Notify Quick Reaction Team (QRT) / Ground Patrol.
   - RESOLVE: Close incident after patrol verification.
   - FALSE POSITIVE: Classify benign trigger with structured feedback.
7. Export secured evidence package (.ZIP) for court filing if required.
```

---

## 2. Managing Cameras & Streaming Infrastructure
- **Adding a Camera**: Navigate to **Cameras -> Add Camera**, specify RTSP URL, camera name, sector, and assign target FPS.
- **Configuring Zones**: In **Zones & Fences**, select the camera, draw polygon boundaries for restricted areas or click two points to create a directional tripwire.
- **Camera Health Monitoring**: Check **System Health** to inspect real-time FPS, decoder latency, dropped frames, and stream uptime.
