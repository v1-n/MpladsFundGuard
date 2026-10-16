def test_list_anomalies(client):
    response = client.get("/api/v1/anomalies?page=1&page_size=10")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "meta" in res
    assert "pagination" in res["meta"]
    assert "disclaimer" in res["meta"]
    items = res["data"]
    assert len(items) == 10
    first = items[0]
    assert "work_id" in first
    assert "rank_in_stage" in first
    assert "anomaly_score" in first
    assert "extreme_feature_indicators" in first

def test_filter_anomalies_by_stage(client):
    response = client.get("/api/v1/anomalies?stage=Completed&page=1&page_size=5")
    assert response.status_code == 200
    res = response.json()
    for it in res["data"]:
        assert it["stage"] == "Completed"

def test_anomaly_detail_existing(client):
    # Fetch first anomaly to get its ID
    response = client.get("/api/v1/anomalies?page=1&page_size=1")
    assert response.status_code == 200
    work_id = response.json()["data"][0]["work_id"]
    
    # Query detail
    detail_res = client.get(f"/api/v1/anomalies/{work_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["work_id"] == work_id
    assert "anomaly_score" in detail
    assert "installments_count" in detail
    assert "primary_vendor" in detail
    assert "methodology_note" in detail
    assert "portal_url" in detail
    assert "photo_compliance_status" in detail
    assert "percentile_in_stage" in detail
    assert detail["portal_url"].startswith("http")
    assert detail["percentile_in_stage"] is not None

def test_anomaly_detail_not_found(client):
    response = client.get("/api/v1/anomalies/NON_EXISTENT_WORK_ID_12345")
    assert response.status_code == 404
    err = response.json()
    assert "error" in err
    assert err["error"]["code"] == "NOT_FOUND"
