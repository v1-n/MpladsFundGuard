# MPLADS FundGuard — Technical Architecture & System Design

## 1. Stack Overview
- **Backend Framework:** FastAPI (Python 3.12, Pydantic v2 schemas)
- **Frontend Framework:** Streamlit (v1.44+, custom glassmorphic CSS theme)
- **Storage & Ingestion:**
  - Artifact Store: Reconciled CSV and JSON artifacts in `data/clean/`
  - Review Store: ACID-compliant SQLite (`data/manual_audit_reviews.db`, WAL journal mode)
- **Machine Learning & Analytics:**
  - Scikit-Learn Isolation Forest ensemble (10 seeds, max_samples=1024)
  - Non-parametric Robust Z-score baseline
  - Pandas & NumPy for vectorized reconciliation

## 2. Request Flow
```
Browser / Auditor
      │
      ▼
Streamlit Frontend (Port 8501)
      │
      │ HTTP REST Requests (Typed ApiClient, Bearer Token Auth)
      ▼
FastAPI Application (Port 8000)
      │
      ├── Dependency: get_current_reviewer (Authenticates Reviewer Sessions)
      ├── Services: OverviewService, AnomalyService, AuditService, etc.
      ├── Repositories: DataRepository (Memory Cached Clean Artifacts)
      └── SQLite: Transactional persistence for manual audit reviews
```

## 3. Core Architectural Principles
1. **Server-Side Authorization & Session Isolation:** Reviewer identity is derived securely from bearer tokens (`Authorization: Bearer <token>` or `X-Reviewer-Token`). Reviewers can only access their own assessments unless authenticated with an admin token.
2. **ACID Transaction Persistence:** Review submissions are executed in SQLite transactions with WAL mode, avoiding flat-file race conditions or corruption.
3. **Quarantined Blind Audit Key:** The true answer key (`manual_audit_sample_key.csv`) is strictly isolated and never exposed to any API route or frontend component.
4. **CSV Injection Defense:** All exported CSV tables neutralize formula execution vectors (`=`, `+`, `-`, `@`, `\t`, `\r`).
5. **Separation of Concerns:** Frontend contains zero direct data processing or database logic; all transformations are executed via backend services.