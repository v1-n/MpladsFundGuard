from fastapi import APIRouter
from backend.app.schemas.common import ResponseEnvelope
from backend.app.schemas.evaluation import ModelEvaluationResponse
from backend.app.services.evaluation_service import evaluation_service
from backend.app.core.config import settings

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[ModelEvaluationResponse])
def get_model_evaluation():
    data = evaluation_service.get_evaluation_results()
    return ResponseEnvelope(
        data=data,
        meta={"disclaimer": settings.DISCLAIMER}
    )
