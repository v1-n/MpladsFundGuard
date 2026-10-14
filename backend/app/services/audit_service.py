import logging
import pandas as pd
from backend.app.core.config import settings
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.audit import (
    AuditSampleResponse,
    BlindAuditItem,
    AuditRubricResponse,
    MatchingDiagnosticsResponse,
)

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, repo=data_repo):
        self.repo = repo

    def get_blind_audit_sample(self) -> AuditSampleResponse:
        df = self.repo.get_blind_audit_sample_df()

        # Strict security check: ensure no leakage
        forbidden = ["Cohort", "rank_in_stage", "anomaly_score"]
        leaked = [c for c in forbidden if c in df.columns]
        if leaked:
            raise RuntimeError(f"Forbidden columns present in blind audit sample: {leaked}")

        items = []
        for _, row in df.iterrows():
            items.append(
                BlindAuditItem(
                    work_id=str(row.get("Work ID", "")),
                    work=str(row.get("Work", "")),
                    state=str(row.get("State", "")),
                    constituency=str(row.get("Constituency", "")),
                    portal_url=str(row.get("Portal_URL", "https://www.mplads.gov.in/")),
                    audit_verdict=str(row.get("Audit_Verdict", "")) if pd.notna(row.get("Audit_Verdict")) else "",
                    auditor_notes=str(row.get("Auditor_Notes", "")) if pd.notna(row.get("Auditor_Notes")) else "",
                )
            )

        instructions = (
            "Reviewers must inspect each work on the official MPLADS portal using Portal_URL, "
            "evaluating completion photos, vendor records, physical asset utility, and payment timelines "
            "against the standardized rubric. Record your verdict ('Normal', 'Irregularity/Suspicious', "
            "'Inefficient/Incomplete') and notes without seeing model rankings or cohort assignments."
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

audit_service = AuditService()
