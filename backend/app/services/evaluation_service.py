import logging
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.evaluation import ModelEvaluationResponse

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self, repo=data_repo):
        self.repo = repo

    def get_evaluation_results(self) -> ModelEvaluationResponse:
        data = self.repo.get_evaluation_results()
        return ModelEvaluationResponse(**data)

evaluation_service = EvaluationService()
