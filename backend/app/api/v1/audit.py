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
    """
    Deliberately unauthenticated endpoint:
    The 100-work audit sample is strictly blinded and contains zero answer keys,
    zero anomaly scores, zero cohort ranks, and zero prior verdicts.
    It serves as open public data to enable transparent community and field review.
    """
    data = audit_service.get_blind_audit_sample()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/rubric", response_model=ResponseEnvelope[AuditRubricResponse])
def get_audit_rubric():
    """
    Deliberately unauthenticated endpoint:
    Public standard evaluation rubric explaining objective criteria for manual classifications.
    """
    data = audit_service.get_audit_rubric()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/diagnostics", response_model=ResponseEnvelope[MatchingDiagnosticsResponse])
def get_audit_diagnostics():
    """
    Deliberately unauthenticated endpoint:
    Aggregate balance statistics (Standardized Mean Differences) for top works vs controls.
    Contains no row-level keys or scoring secrets.
    """
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
    """
    Strictly authenticated:
    Persists reviewer verdict and notes in SQLite with WAL mode, appending an immutable
    record to the historical audit trail. Reviewer identity is derived securely from the authenticated session.
    """
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
    """
    Strictly authenticated:
    Retrieves submitted reviews. Non-admin reviewers are isolated to viewing only their
    own submissions; cross-reviewer data snooping returns 403 Forbidden.
    """
    data = audit_service.get_reviews(
        authenticated_reviewer=current_reviewer,
        target_reviewer_id=reviewer_id,
    )
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )

@router.get("/reviews/history", response_model=ResponseEnvelope[list[dict]])
def get_audit_review_history(
    work_id: Optional[str] = Query(None, description="Filter history by Work ID"),
    reviewer_id: Optional[str] = Query(None, description="Filter history by reviewer ID (admin only)"),
    current_reviewer: AuthenticatedReviewer = Depends(get_current_reviewer),
):
    """
    Strictly authenticated:
    Retrieves the immutable audit trail of review submissions and revisions.
    Non-admin reviewers can only view their own history.
    """
    history = audit_service.get_review_history(
        authenticated_reviewer=current_reviewer,
        work_id=work_id,
        target_reviewer_id=reviewer_id,
    )
    return ResponseEnvelope(
        data=history,
        meta={"disclaimer": settings.DISCLAIMER}
    )
