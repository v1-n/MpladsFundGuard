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

def test_data_quality_all_canonical_rules_supported(client):
    canonical_rules = [
        "duplicate_payment",
        "same_day_bulk",
        "ghost_completion",
        "stalled_unpaid",
        "missing_photo",
        "orphan_payment",
        "cost_cap",
        "date_sequence",
    ]
    for rule in canonical_rules:
        resp = client.get(f"/api/v1/data-quality/findings?flag_type={rule}&page=1&page_size=5")
        assert resp.status_code == 200, f"Rule {rule} query failed with status {resp.status_code}"
        res = resp.json()
        assert "data" in res

def test_data_quality_pagination_bounds_and_consistency(client):
    # Requesting > 200 should fail FastAPIs le=200 validation with 422
    over_res = client.get("/api/v1/data-quality/findings?page=1&page_size=500")
    assert over_res.status_code == 422
    err = over_res.json()
    assert "error" in err
    assert err["error"]["code"] == "VALIDATION_ERROR"

    # Requesting 200 should succeed and accurately reflect page_size in pagination meta
    valid_res = client.get("/api/v1/data-quality/findings?page=1&page_size=200")
    assert valid_res.status_code == 200
    p_meta = valid_res.json()["meta"]["pagination"]
    assert p_meta["page_size"] == 200
    assert p_meta["page"] == 1
    assert p_meta["total_pages"] == (p_meta["total_records"] + 200 - 1) // 200 if p_meta["total_records"] > 0 else 0
