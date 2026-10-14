def test_overview_endpoint(client):
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "meta" in res
    assert "disclaimer" in res["meta"]
    assert "screening signals" in res["meta"]["disclaimer"]
    
    data = res["data"]
    assert data["total_works"] > 0
    assert data["completed_works"] > 0
    assert data["in_progress_works"] > 0
    assert data["total_sanctioned_amount"] > 0
    assert data["total_settled_expenditure"] > 0
    assert 0 <= data["overall_utilization_ratio"] <= 1.0
    
    # Assert integrity checks present
    assert "integrity_checks" in data
    assert data["integrity_checks"]["orphan_payments"] == 0
    assert data["integrity_checks"]["status"] == "PASS"
