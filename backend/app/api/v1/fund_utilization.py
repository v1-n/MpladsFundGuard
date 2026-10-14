from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.common import ResponseEnvelope
from backend.app.schemas.fund_utilization import (
    UtilizationSummary,
    StateUtilizationItem,
    CategoryUtilizationItem,
)
from backend.app.services.fund_utilization_service import FundUtilizationService
from backend.app.core.config import settings

router = APIRouter()

@router.get("/summary", response_model=ResponseEnvelope[UtilizationSummary])
def get_utilization_summary():
    data = FundUtilizationService.get_summary()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/by-state", response_model=ResponseEnvelope[list[StateUtilizationItem]])
def get_utilization_by_state(min_works: int = Query(1, ge=1, description="Minimum works to include state")):
    data = FundUtilizationService.get_by_state(min_works=min_works)
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/by-category", response_model=ResponseEnvelope[list[CategoryUtilizationItem]])
def get_utilization_by_category():
    data = FundUtilizationService.get_by_category()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )
