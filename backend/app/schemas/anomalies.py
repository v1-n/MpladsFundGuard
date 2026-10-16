from typing import Optional
from pydantic import BaseModel

class AnomalyItem(BaseModel):
    work_id: str
    stage: str
    rank_in_stage: int
    anomaly_score: float
    extreme_feature_indicators: str
    top_anomalous_factors: str
    state: str
    constituency: str
    mp_name: str
    work: str
    sanction_amount: Optional[float] = None
    total_exp_settled: Optional[float] = None
    total_exp_in_progress: Optional[float] = None
    paid_vs_peer_log: Optional[float] = None
    peer_tier: Optional[str] = None
    peer_median_settled: Optional[float] = None
    n_rule_flags: int
    flags: dict[str, int]

class AnomalyDetail(BaseModel):
    work_id: str
    stage: str
    rank_in_stage: int
    percentile_in_stage: Optional[float] = None
    anomaly_score: float
    extreme_feature_indicators: str
    top_anomalous_factors: str
    state: str
    constituency: str
    mp_name: str
    work: str
    work_description: Optional[str] = None
    work_category: Optional[str] = None
    sanction_amount: Optional[float] = None
    total_exp_settled: Optional[float] = None
    total_exp_in_progress: Optional[float] = None
    utilization_ratio: Optional[float] = None
    cost_variance: Optional[float] = None
    paid_vs_peer_log: Optional[float] = None
    peer_tier: Optional[str] = None
    peer_median_settled: Optional[float] = None
    recommended_date: Optional[str] = None
    sanction_date: Optional[str] = None
    completion_date: Optional[str] = None
    sanction_approval_days: Optional[float] = None
    execution_duration_days: Optional[float] = None
    first_payment_lag_days: Optional[float] = None
    installments_count: int
    settled_count: int
    in_progress_count: int
    vendors_count: int
    primary_vendor: str
    photo_compliance_status: Optional[str] = None
    portal_url: str = "https://www.mplads.gov.in/"
    rule_flags: dict[str, int]
    methodology_note: str
