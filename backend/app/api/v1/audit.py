from fastapi import APIRouter
from backend.app.schemas.common import ResponseEnvelope
from backend.app.schemas.audit import (
    AuditSampleResponse,
    AuditRubricResponse,
    MatchingDiagnosticsResponse,
)
from backend.app.services.audit_service import audit_service
from backend.app.core.config import settings

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
