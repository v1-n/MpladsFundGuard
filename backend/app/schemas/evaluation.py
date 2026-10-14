from typing import Any, Optional
from pydantic import BaseModel

class CohortSizes(BaseModel):
    total_works_matrix: int
    completed_works: int
    in_progress_works: int

class SeedStabilityItem(BaseModel):
    shared_top_300: int
    jaccard_index: float
    status: str

class MethodMetrics(BaseModel):
    roc_auc_mean: float
    roc_auc_std: float
    precision_at_2pct_mean: float
    precision_at_2pct_std: float
    recall_at_2pct_mean: float
    recall_at_2pct_std: float
    type_a_cost_recall_mean: float
    type_a_cost_recall_std: float
    type_b_count_recall_mean: float
    type_b_count_recall_std: float
    type_c_timeline_recall_mean: float
    type_c_timeline_recall_std: float

class SyntheticBenchmark(BaseModel):
    num_trials: int
    train_ratio: float
    test_ratio: float
    num_injected_anomalies: int
    injected_base_rate_pct: float
    isolation_forest: MethodMetrics
    robust_z_score: MethodMetrics

class BaselineAgreement(BaseModel):
    top_300_shared_count: int
    top_300_overlap_pct: float

class ModelEvaluationResponse(BaseModel):
    generated_at: str
    cohort_sizes: CohortSizes
    seed_stability: dict[str, SeedStabilityItem]
    synthetic_benchmark: SyntheticBenchmark
    clean_data_baseline_agreement: BaselineAgreement
    methodology: str
    limitations: str
