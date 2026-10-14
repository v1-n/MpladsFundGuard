from typing import Optional
from pydantic import BaseModel

class IntegrityChecks(BaseModel):
    orphan_payments: int
    cost_cap_violations: int
    date_sequence_violations: int
    status: str

class OverviewKPIs(BaseModel):
    total_works: int
    completed_works: int
    in_progress_works: int
    sanctioned_only_works: int
    pending_only_works: int
    
    total_sanctioned_amount: float
    total_settled_expenditure: float
    total_in_progress_expenditure: float
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
    disclaimer: str
