# MPLADS FundGuard — Project Memory & Active State

## Current State (October 2026)
- **Security & Authorization Pass:** Completed & Hardened.
  - Reviewer authentication (`Authorization: Bearer <token>` / `X-Reviewer-Token`) is enforced strictly via HTTP headers; URL query parameters are rejected.
  - Hardcoded tokens removed; credentials load dynamically from `AUDIT_REVIEWER_TOKENS` in environment or `.env`.
  - Startup lifespan validation fails if authentication is enabled without tokens configured.
  - Constant-time token verification using `hmac.compare_digest`.
  - Reviewer identity is derived securely from the authenticated session; cross-reviewer data snooping is blocked.
  - Migrated review persistence to SQLite with WAL mode (`data/manual_audit_reviews.db`).
  - Added immutable historical audit trail in `audit_review_history` SQLite table.
- **API & Validation Pass:** Completed.
  - Aligned `page_size` max to `PAGE_SIZE_MAX = 200` with 422 rejection for excess.
  - Enforced allowlisted column sorting with 422 rejection for unapproved fields.
  - Deliberately documented open public access for blinded sample, rubric, and diagnostics.
- **Docker & Packaging Pass:** Completed.
  - Pinned exact runtime dependency versions in `requirements.txt`.
  - Separated test dependencies into `requirements-dev.txt` (excluding `pytest` from container runtime).
  - Modernized `docker-compose.yml` (removed obsolete `version` key).
  - Configured `Dockerfile.backend` to use `HOST` and `PORT` environment variables dynamically.
- **Testing & Verification:**
  - 55/55 automated unit, integration, security, and UI smoke tests pass cleanly.