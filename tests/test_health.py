def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "MPLADS FundGuard" in data["app"]
    assert "disclaimer" in data
    assert "screening signals" in data["disclaimer"]
