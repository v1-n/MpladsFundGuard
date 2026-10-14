from fastapi import APIRouter
from backend.app.schemas.common import ResponseEnvelope
from backend.app.schemas.overview import OverviewKPIs
from backend.app.services.overview_service import OverviewService
from backend.app.core.config import settings

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[OverviewKPIs])
def get_overview_kpis():
    data = OverviewService.get_overview_kpis()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )
