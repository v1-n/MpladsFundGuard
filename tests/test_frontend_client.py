import pytest
import httpx
from frontend.api_client import FundGuardAPIClient, APIError

def test_api_client_handles_503_rebuild():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": {"code": "ARTIFACT_MISSING", "message": "Required data artifact 'mplads_360_master.csv' is not present. Please run: python -m src.rebuild"}}
        )

    client = FundGuardAPIClient(base_url="http://mock-server/api/v1")
    with httpx.Client(transport=httpx.MockTransport(mock_transport)) as mock_http:
        resp = mock_http.get("http://mock-server/api/v1/overview")
        with pytest.raises(APIError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 503
        assert exc_info.value.is_rebuild_needed is True
        assert "python -m src.rebuild" in exc_info.value.message

def test_api_client_handles_404():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": {"code": "NOT_FOUND", "message": "Work not found"}}
        )

    client = FundGuardAPIClient(base_url="http://mock-server/api/v1")
    with httpx.Client(transport=httpx.MockTransport(mock_transport)) as mock_http:
        resp = mock_http.get("http://mock-server/api/v1/anomalies/unknown")
        with pytest.raises(APIError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 404
        assert "Work not found" in exc_info.value.message

def test_api_client_audit_review_methods():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "audit/reviews" in str(request.url):
            return httpx.Response(
                201,
                json={"data": {"work_id": "WS/1", "reviewer_id": "Rev1", "verdict": "Normal / Regular", "notes": "", "updated_at": "2026-10-14T11:00:00Z"}}
            )
        elif request.method == "GET" and "audit/reviews" in str(request.url):
            return httpx.Response(
                200,
                json={"data": {"total_reviews": 1, "reviews": [{"work_id": "WS/1", "reviewer_id": "Rev1", "verdict": "Normal / Regular", "notes": "", "updated_at": "2026-10-14T11:00:00Z"}]}}
            )
        return httpx.Response(404)

    client = FundGuardAPIClient(base_url="http://mock-server/api/v1")
    client._client = httpx.Client(transport=httpx.MockTransport(mock_transport))

    rec = client.submit_audit_review("WS/1", "Rev1", "Normal / Regular", "")
    assert rec["work_id"] == "WS/1"
    assert rec["verdict"] == "Normal / Regular"

    reviews = client.get_audit_reviews(reviewer_id="Rev1")
    assert len(reviews) == 1
    assert reviews[0]["reviewer_id"] == "Rev1"
