from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from backend.app.schemas.common import ResponseEnvelope
from backend.app.schemas.audit import (
    AuditSampleResponse,
    AuditRubricResponse,
    MatchingDiagnosticsResponse,
    AuditReviewSubmission,
    AuditReviewRecord,
    AuditReviewListResponse,
)
from backend.app.services.audit_service import audit_service
from backend.app.core.config import settings
from backend.app.core.auth import AuthenticatedReviewer, get_current_reviewer

router = APIRouter()

@router.get("/sample", response_model=ResponseEnvelope[AuditSampleResponse])
def get_blind_audit_sample():
    data = audit_service.get_blind_audit_sample()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/rubric", response_model=ResponseEnvelope[AuditRubricResponse])
def get_audit_rubric():
    data = audit_service.get_audit_rubric()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/diagnostics", response_model=ResponseEnvelope[MatchingDiagnosticsResponse])
def get_audit_diagnostics():
    data = audit_service.get_audit_diagnostics()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.post("/reviews", response_model=ResponseEnvelope[AuditReviewRecord], status_code=status.HTTP_201_CREATED)
def submit_audit_review(
    submission: AuditReviewSubmission,
    current_reviewer: AuthenticatedReviewer = Depends(get_current_reviewer),
):
    record = audit_service.submit_review(
        submission=submission,
        authenticated_reviewer=current_reviewer,
    )
    return ResponseEnvelope(
        data=record,
        meta={"message": "Audit review successfully persisted."}
    )

@router.get("/reviews", response_model=ResponseEnvelope[AuditReviewListResponse])
def get_audit_reviews(
    reviewer_id: Optional[str] = Query(None, description="Filter reviews by reviewer ID (admin only)"),
    current_reviewer: AuthenticatedReviewer = Depends(get_current_reviewer),
):
    data = audit_service.get_reviews(
        authenticated_reviewer=current_reviewer,
        target_reviewer_id=reviewer_id,
    )
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )
