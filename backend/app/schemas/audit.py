from typing import Optional
from pydantic import BaseModel, Field

class BlindAuditItem(BaseModel):
    work_id: str
    work: str
    state: str
    constituency: str
    portal_url: str

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

class AuditReviewSubmission(BaseModel):
    work_id: str = Field(..., min_length=3, max_length=150, description="Unique Work ID")
    reviewer_id: Optional[str] = Field(default=None, max_length=100, description="Optional reviewer ID; derived from authenticated session if omitted.")
    verdict: str = Field(..., description="Audit verdict: Normal / Regular, Irregularity / Suspicious, Inefficient / Incomplete, Inconsistent Data")
    notes: Optional[str] = Field(default="", max_length=5000, description="Reviewer findings and observations")

class AuditReviewRecord(BaseModel):
    work_id: str
    reviewer_id: str
    verdict: str
    notes: str
    updated_at: str

class AuditReviewListResponse(BaseModel):
    total_reviews: int
    reviews: list[AuditReviewRecord]
