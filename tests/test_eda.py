def test_eda_summary(client):
    response = client.get("/api/v1/eda/summary")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    assert "datasets" in data
    assert len(data["datasets"]) >= 5
    assert "lifecycle_breakdown" in data
    assert "work_status_breakdown" in data
    assert "work_category_top_10" in data
    assert "state_top_10" in data

def test_eda_missing_values(client):
    response = client.get("/api/v1/eda/missing-values?dataset=master")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "missing_fields" in res["data"]

def test_eda_distributions(client):
    response = client.get("/api/v1/eda/distributions")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    for feat in ["sanction_amount", "settled_expenditure", "execution_duration_days", "utilization_ratio"]:
        assert feat in data
        assert "bins" in data[feat]
        assert "counts" in data[feat]
        assert len(data[feat]["bins"]) > 0
