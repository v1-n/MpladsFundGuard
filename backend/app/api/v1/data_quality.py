from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.common import ResponseEnvelope, PaginationMeta
from backend.app.schemas.data_quality import QualitySummary, RuleFindingItem
from backend.app.services.data_quality_service import DataQualityService
from backend.app.core.config import settings

router = APIRouter()

@router.get("/summary", response_model=ResponseEnvelope[QualitySummary])
def get_data_quality_summary():
    data = DataQualityService.get_summary()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/findings", response_model=ResponseEnvelope[list[RuleFindingItem]])
def get_data_quality_findings(
    flag_type: Optional[str] = Query(None, description="Filter rule: duplicate_payment, same_day_bulk, ghost_completion, stalled_unpaid, missing_photo, orphan_payment, cost_cap, date_sequence"),
    state: Optional[str] = Query(None, description="State filter"),
    category: Optional[str] = Query(None, description="Work category filter"),
    sort_by: str = Query("Sanction_Amount", description="Sort column"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=settings.PAGE_SIZE_MAX, description=f"Page size (max {settings.PAGE_SIZE_MAX})"),
):
    findings, total_records, effective_page_size = DataQualityService.get_findings(
        flag_type=flag_type,
        state=state,
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total_pages = (total_records + effective_page_size - 1) // effective_page_size if total_records > 0 else 0
    return ResponseEnvelope(
        data=findings,
        meta={
            "disclaimer": settings.DISCLAIMER,
            "pagination": {
                "total_records": total_records,
                "page": page,
                "page_size": effective_page_size,
                "total_pages": total_pages,
            }
        }
    )
