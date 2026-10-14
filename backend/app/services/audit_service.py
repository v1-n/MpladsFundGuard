import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.errors import AppException
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
    def __init__(self, repo=data_repo, storage_path: Optional[Path] = None):
        self.repo = repo
        self.storage_path = storage_path or (settings.DATA_DIR / "manual_audit_reviews.json")

    def get_blind_audit_sample(self) -> AuditSampleResponse:
        df = self.repo.get_blind_audit_sample_df()

        # Strict security check: ensure no leakage of answer key or model ranks
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

    def _load_stored_reviews(self) -> list[dict]:
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading audit reviews from {self.storage_path}: {e}")
            return []

    def _save_stored_reviews(self, reviews: list[dict]):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.storage_path)

    def submit_review(self, submission: AuditReviewSubmission) -> AuditReviewRecord:
        verdict = submission.verdict.strip()
        if verdict not in ALLOWED_VERDICTS:
            raise AppException(
                code="INVALID_VERDICT",
                message=f"Verdict '{verdict}' is not allowed. Must be one of: {sorted(list(ALLOWED_VERDICTS))}",
                status_code=400,
            )

        # Ensure work_id exists in the blind sample
        sample_df = self.repo.get_blind_audit_sample_df()
        valid_work_ids = set(sample_df["Work ID"].astype(str).str.strip())
        if submission.work_id.strip() not in valid_work_ids:
            raise AppException(
                code="WORK_NOT_IN_SAMPLE",
                message=f"Work ID '{submission.work_id}' is not in the active blind audit sample.",
                status_code=404,
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        record_dict = {
            "work_id": submission.work_id.strip(),
            "reviewer_id": submission.reviewer_id.strip(),
            "verdict": verdict,
            "notes": (submission.notes or "").strip(),
            "updated_at": now_iso,
        }

        reviews = self._load_stored_reviews()
        # Upsert by (work_id, reviewer_id)
        updated = False
        for i, r in enumerate(reviews):
            if r.get("work_id") == record_dict["work_id"] and r.get("reviewer_id") == record_dict["reviewer_id"]:
                reviews[i] = record_dict
                updated = True
                break
        if not updated:
            reviews.append(record_dict)

        self._save_stored_reviews(reviews)
        return AuditReviewRecord(**record_dict)

    def get_reviews(self, reviewer_id: Optional[str] = None) -> AuditReviewListResponse:
        reviews_data = self._load_stored_reviews()
        if reviewer_id:
            req_rev = reviewer_id.strip().lower()
            reviews_data = [r for r in reviews_data if r.get("reviewer_id", "").strip().lower() == req_rev]

        records = [AuditReviewRecord(**r) for r in reviews_data]
        return AuditReviewListResponse(
            total_reviews=len(records),
            reviews=records,
        )

audit_service = AuditService()
