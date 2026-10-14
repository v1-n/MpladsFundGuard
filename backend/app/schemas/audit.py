from typing import Optional
from pydantic import BaseModel

class BlindAuditItem(BaseModel):
    work_id: str
    work: str
    state: str
    constituency: str
    portal_url: str
    audit_verdict: Optional[str] = ""
    auditor_notes: Optional[str] = ""

class AuditSampleResponse(BaseModel):
    total_samples: int
    instructions: str
    disclaimer: str
    sample: list[BlindAuditItem]

class AuditRubricResponse(BaseModel):
    rubric_markdown: str

class MatchingDiagnosticsResponse(BaseModel):
    generated_at: str
    n_top_ranked: int
    n_matched_controls: int
    top_50_medians: dict[str, float]
    control_medians: dict[str, float]
    standardized_mean_differences: dict[str, float]
    controls_min_rank: float
    imbalance_warning: bool
    notes: str
