def test_fund_utilization_summary(client):
    response = client.get("/api/v1/fund-utilization/summary")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    assert data["total_sanctioned"] > 0
    assert data["total_settled"] > 0
    assert 0 <= data["overall_utilization_pct"] <= 100

def test_fund_utilization_by_state(client):
    response = client.get("/api/v1/fund-utilization/by-state?min_works=10")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    items = res["data"]
    assert len(items) > 0
    for it in items:
        assert "state" in it
        assert "works_count" in it
        assert it["works_count"] >= 10
        assert "utilization_pct" in it

def test_fund_utilization_by_category(client):
    response = client.get("/api/v1/fund-utilization/by-category")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    items = res["data"]
    assert len(items) > 0
    for it in items:
        assert "category" in it
        assert "peer_benchmark_tier_distribution" in it
