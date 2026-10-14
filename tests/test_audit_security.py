def test_audit_sample_is_blind_and_has_no_key_columns(client):
    response = client.get("/api/v1/audit/sample")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    
    assert data["total_samples"] == 100
    assert len(data["sample"]) == 100
    
    # Check that forbidden columns NEVER leak into any item
    forbidden_keys = {"cohort", "Cohort", "rank_in_stage", "anomaly_score", "score", "rank"}
    for item in data["sample"]:
        item_keys = set(item.keys())
        assert not (item_keys & forbidden_keys), f"Leaked forbidden keys: {item_keys & forbidden_keys}"
        assert "work_id" in item
        assert "work" in item
        assert "state" in item
        assert "constituency" in item
        assert "portal_url" in item

def test_audit_rubric(client):
    response = client.get("/api/v1/audit/rubric")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "rubric_markdown" in res["data"]
    assert "Manual Audit Review Rubric" in res["data"]["rubric_markdown"]

def test_audit_diagnostics(client):
    response = client.get("/api/v1/audit/diagnostics")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    diag = res["data"]
    assert diag["n_top_ranked"] == 50
    assert diag["n_matched_controls"] == 50
    assert diag["controls_min_rank"] >= 300
    assert "standardized_mean_differences" in diag

def test_audit_key_not_exposed(client):
    # Ensure there is no endpoint that exposes the key
    for path in ["/api/v1/audit/key", "/api/v1/audit/sample/key", "/api/v1/key", "/data/clean/manual_audit_sample_key.csv"]:
        res = client.get(path)
        assert res.status_code in [404, 405]
