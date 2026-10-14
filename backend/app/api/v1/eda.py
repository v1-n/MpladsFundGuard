from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.common import ResponseEnvelope
from backend.app.schemas.eda import EDASummary, MissingValuesResponse, EDADistributions
from backend.app.services.eda_service import EDAService
from backend.app.core.config import settings

router = APIRouter()

@router.get("/summary", response_model=ResponseEnvelope[EDASummary])
def get_eda_summary():
    data = EDAService.get_summary()
    return ResponseEnvelope(data=data, meta={"disclaimer": settings.DISCLAIMER})

@router.get("/missing-values", response_model=ResponseEnvelope[MissingValuesResponse])
def get_eda_missing_values(dataset: str = Query("master", description="Dataset name: master, sanctioned, expenditure, completed, mp")):
    data = EDAService.get_missing_values(dataset)
    return ResponseEnvelope(data=data, meta={"dataset": dataset})

@router.get("/distributions", response_model=ResponseEnvelope[EDADistributions])
def get_eda_distributions():
    data = EDAService.get_distributions()
    return ResponseEnvelope(data=data, meta={"disclaimer": settings.DISCLAIMER})
