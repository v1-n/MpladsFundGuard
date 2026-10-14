from typing import Any, Optional
from pydantic import BaseModel

class DatasetMetric(BaseModel):
    name: str
    rows: int
    columns: int
    column_names: list[str]

class EDASummary(BaseModel):
    datasets: list[DatasetMetric]
    lifecycle_breakdown: dict[str, int]
    work_status_breakdown: dict[str, int]
    work_category_top_10: dict[str, int]
    state_top_10: dict[str, int]

class MissingValueItem(BaseModel):
    column: str
    missing_count: int
    missing_pct: float
    total_count: int

class MissingValuesResponse(BaseModel):
    dataset_name: str
    missing_fields: list[MissingValueItem]

class DistributionHistogram(BaseModel):
    feature: str
    bins: list[float]
    counts: list[int]
    min_val: float
    max_val: float
    mean_val: float
    median_val: float

class EDADistributions(BaseModel):
    sanction_amount: DistributionHistogram
    settled_expenditure: DistributionHistogram
    execution_duration_days: DistributionHistogram
    utilization_ratio: DistributionHistogram
