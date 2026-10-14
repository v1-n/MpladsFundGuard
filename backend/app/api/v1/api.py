from fastapi import APIRouter
from backend.app.api.v1 import (
    overview,
    eda,
    data_quality,
    fund_utilization,
    anomalies,
    evaluation,
    audit,
)

api_router = APIRouter()

api_router.include_router(overview.router, prefix="/overview", tags=["Overview"])
api_router.include_router(eda.router, prefix="/eda", tags=["EDA"])
api_router.include_router(data_quality.router, prefix="/data-quality", tags=["Data Quality"])
api_router.include_router(fund_utilization.router, prefix="/fund-utilization", tags=["Fund Utilization"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["Anomalies"])
api_router.include_router(evaluation.router, prefix="/model-evaluation", tags=["Model Evaluation"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
