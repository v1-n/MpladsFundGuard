# MPLADS FundGuard — Project Memory & Active State

## Current State (October 2026)
- **Security & Authorization Pass:** Completed.
  - Reviewer authentication (`Authorization: Bearer <token>` / `X-Reviewer-Token`) is enforced.
  - Reviewer identity is derived securely from the authenticated session.
  - Cross-reviewer review data snooping is blocked; admin role controls multi-reviewer views.
  - Migrated review persistence from flat JSON to SQLite with WAL mode (`data/manual_audit_reviews.db`).
- **Data & Provenance Pass:** Completed.
  - Hardcoded pipeline counts eliminated from schemas, services, and frontend pages.
  - Dynamic provenance tracks real artifact timestamps and file existence.
  - Data grains reconciled with 0.00 discrepancy (₹44,515,171,891.91 sanction, ₹28,645,709,664.45 settled disbursements).
- **Traceable Dossier Pass:** Completed.
  - Restructured `5_Anomaly_Screening.py` into 4 distinct evidence panels:
    1. Observed Public Ledger Evidence (with MoSPI portal links and photo compliance)
    2. Statistical Outlier Deviations & Peer Comparisons
    3. Deterministic Ledger Integrity Rule Flags
    4. Human Review & Case Actions
- **Testing & Verification:**
  - 49/49 automated unit, integration, security, and UI smoke tests pass cleanly.