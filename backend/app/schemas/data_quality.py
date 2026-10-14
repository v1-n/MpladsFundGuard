from typing import Optional, Any
from pydantic import BaseModel

class QualityCheckItem(BaseModel):
    check_number: int
    check_name: str
    status: str
    message: str
    detail: Optional[str] = None
    count: Optional[int] = None
    is_output_gate: bool

class QualitySummary(BaseModel):
    total_checks: int
    passed: int
    warnings: int
    failures: int
    input_warnings: int
    output_warnings: int
    overall_status: str
    checks: list[QualityCheckItem]

class RuleFindingItem(BaseModel):
    work_id: str
    state: str
    constituency: str
    mp_name: str
    work: str
    sanction_amount: Optional[float] = None
    total_exp_settled: Optional[float] = None
    rule_flag_type: str
    reason: str
    installments: int
    vendors: int
    primary_vendor: str
    completion_date: Optional[str] = None

class RuleFindingsResponse(BaseModel):
    findings: list[RuleFindingItem]
