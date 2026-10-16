from typing import Optional, Literal
from fastapi import APIRouter, Query, Path
from backend.app.schemas.common import ResponseEnvelope, PaginationMeta
from backend.app.schemas.anomalies import AnomalyItem, AnomalyDetail
from backend.app.services.anomaly_service import AnomalyService
from backend.app.core.config import settings

router = APIRouter()

SortByField = Literal[
    "rank_in_stage",
    "anomaly_score",
    "sanction_amount",
    "total_exp_settled",
    "total_exp_in_progress",
    "paid_vs_peer_log",
    "work_id",
    "state",
    "constituency",
    "n_rule_flags",
]
SortOrder = Literal["asc", "desc"]

@router.get("", response_model=ResponseEnvelope[list[AnomalyItem]])
def list_anomalies(
    stage: Optional[str] = Query(None, description="Completed or In-Progress"),
    state: Optional[str] = Query(None, description="State filter"),
    category: Optional[str] = Query(None, description="Work text search or category"),
    min_score: Optional[float] = Query(None, description="Minimum anomaly score"),
    max_score: Optional[float] = Query(None, description="Maximum anomaly score"),
    search: Optional[str] = Query(None, description="Search work id, work description, constituency, MP"),
    sort_by: SortByField = Query("rank_in_stage", description="Allowlisted column to sort by"),
    sort_order: SortOrder = Query("asc", description="asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX, description=f"Page size (max {settings.PAGE_SIZE_MAX})"),
):
    items, total_records = AnomalyService.get_anomalies(
        stage=stage,
        state=state,
        category=category,
        min_score=min_score,
        max_score=max_score,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
    return ResponseEnvelope(
        data=items,
        meta={
            "disclaimer": settings.DISCLAIMER,
            "pagination": {
                "total_records": total_records,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }
    )

@router.get("/{work_id:path}", response_model=ResponseEnvelope[AnomalyDetail])
def get_anomaly_detail(
    work_id: str = Path(..., description="Unique Work ID, e.g. WS/MP18170/2024-2025/156350")
):
    detail = AnomalyService.get_anomaly_detail(work_id=work_id)
    return ResponseEnvelope(
        data=detail,
        meta={"disclaimer": settings.DISCLAIMER}
    )
