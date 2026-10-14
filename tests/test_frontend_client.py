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
    # Test through a custom client with mocked transport
    with httpx.Client(transport=httpx.MockTransport(mock_transport)) as mock_http:
        # Override _handle_response behavior with mock response
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
