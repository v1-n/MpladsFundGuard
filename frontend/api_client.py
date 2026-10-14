import os
import logging
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
API_V1_URL = f"{BACKEND_BASE_URL}/api/v1"

class APIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, is_rebuild_needed: bool = False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_rebuild_needed = is_rebuild_needed

class FundGuardAPIClient:
    def __init__(self, base_url: str = API_V1_URL, timeout: float = 25.0):
        self.base_url = base_url.rstrip("/")
        self.root_url = BACKEND_BASE_URL.rstrip("/")
        self.timeout = timeout

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 503:
            try:
                err_body = response.json()
                msg = err_body.get("error", {}).get("message", "Artifact missing.")
            except Exception:
                msg = response.text
            raise APIError(
                message=f"{msg} (Run 'python -m src.rebuild' to generate pipeline artifacts)",
                status_code=503,
                is_rebuild_needed=True,
            )
        if response.status_code >= 400:
            try:
                err_body = response.json()
                msg = err_body.get("error", {}).get("message", response.text)
            except Exception:
                msg = response.text
            raise APIError(message=f"API Error ({response.status_code}): {msg}", status_code=response.status_code)

        try:
            return response.json()
        except Exception as e:
            raise APIError(f"Failed to parse JSON response: {e}")

    def check_health(self) -> dict:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.get(f"{self.root_url}/health")
                return self._handle_response(r)
        except httpx.ConnectError:
            raise APIError("Cannot connect to Backend API. Please verify FastAPI is running at " + self.root_url)
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {e}")

    def get_overview(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/overview")
            return self._handle_response(r).get("data", {})

    def get_eda_summary(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/eda/summary")
            return self._handle_response(r).get("data", {})

    def get_eda_missing_values(self, dataset: str = "master") -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/eda/missing-values", params={"dataset": dataset})
            return self._handle_response(r).get("data", {})

    def get_eda_distributions(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/eda/distributions")
            return self._handle_response(r).get("data", {})

    def get_data_quality_summary(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/data-quality/summary")
            return self._handle_response(r).get("data", {})

    def get_data_quality_findings(
        self,
        flag_type: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "Sanction_Amount",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], dict]:
        params = {
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "page_size": page_size,
        }
        if flag_type:
            params["flag_type"] = flag_type
        if state:
            params["state"] = state
        if category:
            params["category"] = category

        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/data-quality/findings", params=params)
            res = self._handle_response(r)
            return res.get("data", []), res.get("meta", {}).get("pagination", {})

    def get_fund_utilization_summary(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/fund-utilization/summary")
            return self._handle_response(r).get("data", {})

    def get_fund_utilization_by_state(self, min_works: int = 1) -> list[dict]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/fund-utilization/by-state", params={"min_works": min_works})
            return self._handle_response(r).get("data", [])

    def get_fund_utilization_by_category(self) -> list[dict]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/fund-utilization/by-category")
            return self._handle_response(r).get("data", [])

    def get_anomalies(
        self,
        stage: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: str = "rank_in_stage",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], dict]:
        params = {
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "page_size": page_size,
        }
        if stage:
            params["stage"] = stage
        if state:
            params["state"] = state
        if category:
            params["category"] = category
        if min_score is not None:
            params["min_score"] = min_score
        if max_score is not None:
            params["max_score"] = max_score
        if search:
            params["search"] = search

        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/anomalies", params=params)
            res = self._handle_response(r)
            return res.get("data", []), res.get("meta", {}).get("pagination", {})

    def get_anomaly_detail(self, work_id: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/anomalies/{work_id}")
            return self._handle_response(r).get("data", {})

    def get_model_evaluation(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/model-evaluation")
            return self._handle_response(r).get("data", {})

    def get_blind_audit_sample(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/audit/sample")
            return self._handle_response(r).get("data", {})

    def get_audit_rubric(self) -> str:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/audit/rubric")
            return self._handle_response(r).get("data", {}).get("rubric_markdown", "")

    def get_audit_diagnostics(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/audit/diagnostics")
            return self._handle_response(r).get("data", {})

# Singleton instance for the frontend
api_client = FundGuardAPIClient()
