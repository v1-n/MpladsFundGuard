import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.core.auth import AuthenticatedReviewer
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.audit import (
    AuditSampleResponse,
    BlindAuditItem,
    AuditRubricResponse,
    MatchingDiagnosticsResponse,
    AuditReviewSubmission,
    AuditReviewRecord,
    AuditReviewListResponse,
)

logger = logging.getLogger(__name__)

ALLOWED_VERDICTS = {
    "Normal / Regular",
    "Irregularity / Suspicious",
    "Inefficient / Incomplete",
    "Inconsistent Data",
}


class AuditService:
    def __init__(self, repo=data_repo, db_path: Optional[Path] = None):
        self.repo = repo
        self.db_path = db_path or settings.AUDIT_DB_PATH
        self._init_sqlite_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_sqlite_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_reviews (
                    work_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (work_id, reviewer_id)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_reviews_reviewer ON audit_reviews(reviewer_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_reviews_work ON audit_reviews(work_id);")

        # Migrate legacy reviews from JSON if table is newly created and legacy JSON exists
        self._migrate_legacy_json_if_needed()

    def _migrate_legacy_json_if_needed(self):
        legacy_json = settings.DATA_DIR / "manual_audit_reviews.json"
        if not legacy_json.exists():
            return
        try:
            with self._get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM audit_reviews;").fetchone()[0]
                if count == 0:
                    with open(legacy_json, "r", encoding="utf-8") as f:
                        records = json.load(f)
                    for r in records:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO audit_reviews (work_id, reviewer_id, verdict, notes, updated_at)
                            VALUES (?, ?, ?, ?, ?);
                            """,
                            (
                                r.get("work_id", "").strip(),
                                r.get("reviewer_id", "").strip(),
                                r.get("verdict", "").strip(),
                                r.get("notes", "").strip(),
                                r.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            ),
                        )
                    logger.info(f"Successfully migrated {len(records)} legacy reviews from JSON to SQLite.")
        except Exception as e:
            logger.warning(f"Could not migrate legacy reviews JSON: {e}")

    def get_blind_audit_sample(self) -> AuditSampleResponse:
        df = self.repo.get_blind_audit_sample_df()

        # Strict security check: ensure no leakage of answer key, model ranks, scores, or cohorts
        forbidden = ["Cohort", "rank_in_stage", "anomaly_score", "score", "rank"]
        leaked = [c for c in forbidden if c in df.columns]
        if leaked:
            raise RuntimeError(f"CRITICAL: Forbidden columns present in blind audit sample: {leaked}")

        items = []
        for _, row in df.iterrows():
            items.append(
                BlindAuditItem(
                    work_id=str(row.get("Work ID", "")),
                    work=str(row.get("Work", "")),
                    state=str(row.get("State", "")),
                    constituency=str(row.get("Constituency", "")),
                    portal_url=str(row.get("Portal_URL", "https://www.mplads.gov.in/")),
                )
            )

        instructions = (
            "Reviewers must inspect each work on the official MPLADS portal using Portal_URL, "
            "evaluating completion photos, vendor records, physical asset utility, and payment timelines "
            "against the standardized rubric. Record your verdict ('Normal / Regular', 'Irregularity / Suspicious', "
            "'Inefficient / Incomplete', 'Inconsistent Data') and notes without seeing model rankings or cohort assignments."
        )

        return AuditSampleResponse(
            total_samples=len(items),
            instructions=instructions,
            disclaimer=settings.DISCLAIMER,
            sample=items,
        )

    def get_audit_rubric(self) -> AuditRubricResponse:
        rubric_md = self.repo.get_audit_rubric()
        return AuditRubricResponse(rubric_markdown=rubric_md)

    def get_audit_diagnostics(self) -> MatchingDiagnosticsResponse:
        data = self.repo.get_audit_diagnostics()
        return MatchingDiagnosticsResponse(**data)

    def submit_review(
        self,
        submission: AuditReviewSubmission,
        authenticated_reviewer: AuthenticatedReviewer,
    ) -> AuditReviewRecord:
        verdict = submission.verdict.strip()
        if verdict not in ALLOWED_VERDICTS:
            raise AppException(
                code="INVALID_VERDICT",
                message=f"Verdict '{verdict}' is not allowed. Must be one of: {sorted(list(ALLOWED_VERDICTS))}",
                status_code=400,
            )

        # Validate that work_id exists in the authorized blind sample
        sample_df = self.repo.get_blind_audit_sample_df()
        valid_work_ids = set(sample_df["Work ID"].astype(str).str.strip())
        work_id = submission.work_id.strip()
        if work_id not in valid_work_ids:
            raise AppException(
                code="WORK_NOT_IN_SAMPLE",
                message=f"Work ID '{work_id}' is not in the active blind audit sample.",
                status_code=404,
            )

        # Derive reviewer identity from authenticated session to prevent impersonation
        if submission.reviewer_id and submission.reviewer_id.strip().lower() != authenticated_reviewer.reviewer_id.lower():
            if authenticated_reviewer.role != "admin":
                raise AppException(
                    code="FORBIDDEN_IMPERSONATION",
                    message="Reviewers cannot submit audit reviews on behalf of other reviewers.",
                    status_code=403,
                )
            effective_reviewer_id = submission.reviewer_id.strip()
        else:
            effective_reviewer_id = authenticated_reviewer.reviewer_id

        now_iso = datetime.now(timezone.utc).isoformat()
        notes = (submission.notes or "").strip()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_reviews (work_id, reviewer_id, verdict, notes, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_id, reviewer_id) DO UPDATE SET
                    verdict = excluded.verdict,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at;
                """,
                (work_id, effective_reviewer_id, verdict, notes, now_iso),
            )

        return AuditReviewRecord(
            work_id=work_id,
            reviewer_id=effective_reviewer_id,
            verdict=verdict,
            notes=notes,
            updated_at=now_iso,
        )

    def get_reviews(
        self,
        authenticated_reviewer: AuthenticatedReviewer,
        target_reviewer_id: Optional[str] = None,
    ) -> AuditReviewListResponse:
        # Authorization check: non-admin reviewers may only retrieve their own reviews
        if authenticated_reviewer.role != "admin":
            if target_reviewer_id and target_reviewer_id.strip().lower() != authenticated_reviewer.reviewer_id.lower():
                raise AppException(
                    code="FORBIDDEN_ACCESS",
                    message="Standard reviewers are not authorized to view peer reviewers' audit records.",
                    status_code=403,
                )
            filter_reviewer = authenticated_reviewer.reviewer_id
        else:
            filter_reviewer = target_reviewer_id.strip() if target_reviewer_id else None

        with self._get_connection() as conn:
            if filter_reviewer:
                cursor = conn.execute(
                    """
                    SELECT work_id, reviewer_id, verdict, notes, updated_at
                    FROM audit_reviews
                    WHERE LOWER(reviewer_id) = LOWER(?)
                    ORDER BY updated_at DESC;
                    """,
                    (filter_reviewer,),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT work_id, reviewer_id, verdict, notes, updated_at
                    FROM audit_reviews
                    ORDER BY updated_at DESC;
                    """
                )
            rows = cursor.fetchall()

        records = [
            AuditReviewRecord(
                work_id=row["work_id"],
                reviewer_id=row["reviewer_id"],
                verdict=row["verdict"],
                notes=row["notes"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

        return AuditReviewListResponse(
            total_reviews=len(records),
            reviews=records,
        )


audit_service = AuditService()
