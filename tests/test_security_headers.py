def test_cors_configuration(client):
    # Test preflight from allowed Streamlit frontend origin
    headers = {
        "Origin": "http://localhost:8501",
        "Access-Control-Request-Method": "GET"
    }
    response = client.options("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8501"
    
    # Assert credentials wildcard is disabled
    assert response.headers.get("access-control-allow-credentials") is None or response.headers.get("access-control-allow-credentials") == "false"

def test_cors_rejects_unknown_origin(client):
    headers = {
        "Origin": "https://malicious-website.com",
        "Access-Control-Request-Method": "GET"
    }
    response = client.options("/api/v1/overview", headers=headers)
    # FastAPIs CORSMiddleware does not set Access-Control-Allow-Origin header for disallowed origins
    assert response.headers.get("access-control-allow-origin") is None or response.headers.get("access-control-allow-origin") != "https://malicious-website.com"
