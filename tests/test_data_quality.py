def test_data_quality_summary(client):
    response = client.get("/api/v1/data-quality/summary")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    assert "checks" in data
    assert data["total_checks"] >= 14
    assert len(data["checks"]) >= 14
    assert "input_warnings" in data
    assert "output_warnings" in data

def test_data_quality_findings(client):
    response = client.get("/api/v1/data-quality/findings?page=1&page_size=10")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "meta" in res
    assert "pagination" in res["meta"]
    assert len(res["data"]) <= 10
    
    if len(res["data"]) > 0:
        first = res["data"][0]
        assert "work_id" in first
        assert "rule_flag_type" in first
        assert "reason" in first

def test_data_quality_findings_filter(client):
    response = client.get("/api/v1/data-quality/findings?flag_type=duplicate_payment&page=1&page_size=5")
    assert response.status_code == 200
    res = response.json()
    for item in res["data"]:
        assert item["rule_flag_type"] == "Flag_Duplicate_Payment"
