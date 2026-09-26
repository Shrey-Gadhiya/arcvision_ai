# ARC VISION — Security Architecture & Governance

## 1. Authentication & Authorization (RBAC)

ARC VISION implements role-based access control (RBAC) across five operational personas:

| Role | Camera Config | Live Feeds | Incident Triage | Evidence Export | Watchlist Mgt | System Config |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ADMIN** | Full | Full | Full | Full | Full | Full |
| **COMMANDER** | Full | Full | Full | Full | Full | Read |
| **OPERATOR** | Read | Full | Acknowledge/Triage | Read | Read | None |
| **INVESTIGATOR**| None | Read | Forensic Review | Full | Read | None |
| **AUDITOR** | None | Read | Audit Log Review | Verify Only | None | None |

---

## 2. Cryptographic Integrity & Evidence Chain of Custody
1. **Per-Item SHA-256 Hashes**: Every captured snapshot still, cropped identity target, and video segment is hashed immediately upon generation using standard SHA-256.
2. **Tamper-Evident Packages**: Evidence bundles exported via `/api/v1/evidence/export-package` contain a signed `manifest.json` detailing hash signatures, camera IDs, timestamps, and model versioning.
3. **Automated Audit**: The UI and backend provide instantaneous verification tools to compare on-disk file contents against database SHA-256 records.

---

## 3. Data Governance & Biometric Privacy
- **Biometric Minimization**: Facial embeddings are stored as 512-dimensional floating-point vectors rather than raw unencrypted biometrics.
- **Configurable Retention**: Continuous non-event footage is subject to automated retention purging (e.g. 7–30 days), while protected court evidence is locked under operational hold.
- **Audit Logging**: Every operator login, incident status modification, evidence download, and configuration change writes an immutable audit record to the `audit_logs` table.
