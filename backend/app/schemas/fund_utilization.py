from typing import Optional
from pydantic import BaseModel

class UtilizationSummary(BaseModel):
    total_sanctioned: float
    total_settled: float
    total_in_progress: float
    overall_utilization_pct: float
    completed_utilization_pct: float
    in_progress_utilization_pct: float
    total_active_works: int

class StateUtilizationItem(BaseModel):
    state: str
    works_count: int
    sanctioned_amount: float
    settled_amount: float
    in_progress_amount: float
    utilization_pct: float

class CategoryUtilizationItem(BaseModel):
    category: str
    works_count: int
    sanctioned_amount: float
    settled_amount: float
    utilization_pct: float
    peer_benchmark_tier_distribution: dict[str, int]
