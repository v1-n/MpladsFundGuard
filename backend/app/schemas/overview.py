from typing import Optional
from pydantic import BaseModel

class IntegrityChecks(BaseModel):
    orphan_payments: int
    cost_cap_violations: int
    date_sequence_violations: int
    status: str  # PASS, WARN, NOT VERIFIED, UNKNOWN

class PipelineStageItem(BaseModel):
    stage_number: int
    name: str
    description: str
    status: str  # COMPLETED, NOT VERIFIED, UNKNOWN, ACTIVE, PENDING
    artifact_name: Optional[str] = None
    item_count: Optional[int] = None
    updated_at: Optional[str] = None

class PipelineDataCounts(BaseModel):
    raw_source_rows: Optional[int] = None
    cleaned_sanctioned_rows: Optional[int] = None
    cleaned_expenditure_rows: Optional[int] = None
    cleaned_completed_rows: Optional[int] = None
    unique_master_works: Optional[int] = None
    ml_scored_works: Optional[int] = None
    blind_audit_sample_works: Optional[int] = None

class OverviewKPIs(BaseModel):
    total_works: int
    completed_works: int
    in_progress_works: int
    sanctioned_only_works: int
    pending_only_works: int
    
    total_sanctioned_amount: float
    total_settled_expenditure: float
    total_in_progress_expenditure: float
    remaining_unspent_amount: float
    overall_utilization_ratio: float
    
    stalled_unpaid_works: int
    duplicate_payment_works: int
    ghost_completion_works: int
    same_day_bulk_payment_works: int
    
    missing_photos_post_cutoff: int
    missing_photos_pre_cutoff: int
    
    completed_anomalies_top_300: int
    in_progress_anomalies_top_300: int
    
    integrity_checks: IntegrityChecks
    pipeline_counts: Optional[PipelineDataCounts] = None
    pipeline_stages: Optional[list[PipelineStageItem]] = None
    data_provenance: Optional[dict[str, str]] = None
    disclaimer: str
