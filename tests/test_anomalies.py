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

def test_anomalies_page_size_max_rejected(client):
    # Requesting page_size greater than PAGE_SIZE_MAX (200) should be rejected with 422
    response = client.get("/api/v1/anomalies?page_size=201")
    assert response.status_code == 422
    response_500 = client.get("/api/v1/anomalies?page_size=500")
    assert response_500.status_code == 422

def test_anomalies_sort_by_allowlist_validation(client):
    # Allowed sort field should succeed
    response_ok = client.get("/api/v1/anomalies?sort_by=anomaly_score&sort_order=desc&page_size=5")
    assert response_ok.status_code == 200
    # Unapproved or internal column should be rejected with 422
    response_invalid = client.get("/api/v1/anomalies?sort_by=internal_secret_col")
    assert response_invalid.status_code == 422
