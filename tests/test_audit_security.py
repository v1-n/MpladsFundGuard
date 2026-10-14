def test_audit_sample_is_strictly_blind_and_has_no_prior_verdicts(client):
    response = client.get("/api/v1/audit/sample")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    
    assert data["total_samples"] == 100
    assert len(data["sample"]) == 100
    
    # Complete response schema check: ONLY identification and inspection fields are returned
    allowed_keys = {"work_id", "work", "state", "constituency", "portal_url"}
    for item in data["sample"]:
        item_keys = set(item.keys())
        assert item_keys == allowed_keys, f"Blind item has unexpected fields: {item_keys - allowed_keys}"
        # Explicit check that verdicts and notes never leak into the blind sample
        assert "audit_verdict" not in item
        assert "auditor_notes" not in item
        assert "cohort" not in item
        assert "anomaly_score" not in item

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
    # Ensure there is no endpoint that exposes the answer key
    for path in ["/api/v1/audit/key", "/api/v1/audit/sample/key", "/api/v1/key", "/data/clean/manual_audit_sample_key.csv"]:
        res = client.get(path)
        assert res.status_code in [404, 405]

def test_audit_review_persistence_workflow(client):
    # 1. Fetch first sample work ID
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]
    
    # 2. Submit a review
    payload = {
        "work_id": work_id,
        "reviewer_id": "Auditor-Test-Alpha",
        "verdict": "Normal / Regular",
        "notes": "Verified completion photo on portal dashboard."
    }
    submit_res = client.post("/api/v1/audit/reviews", json=payload)
    assert submit_res.status_code == 201
    record = submit_res.json()["data"]
    assert record["work_id"] == work_id
    assert record["reviewer_id"] == "Auditor-Test-Alpha"
    assert record["verdict"] == "Normal / Regular"
    assert "updated_at" in record

    # 3. Retrieve review by reviewer_id
    get_res = client.get("/api/v1/audit/reviews?reviewer_id=Auditor-Test-Alpha")
    assert get_res.status_code == 200
    reviews = get_res.json()["data"]["reviews"]
    assert len(reviews) >= 1
    found = [r for r in reviews if r["work_id"] == work_id]
    assert len(found) == 1
    assert found[0]["verdict"] == "Normal / Regular"

def test_audit_review_invalid_verdict_rejected(client):
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]
    
    payload = {
        "work_id": work_id,
        "reviewer_id": "Auditor-Test-Alpha",
        "verdict": "Totally Fraudulent Verdict Not Allowed",
        "notes": "Invalid verdict"
    }
    submit_res = client.post("/api/v1/audit/reviews", json=payload)
    assert submit_res.status_code == 400
    err = submit_res.json()
    assert err["error"]["code"] == "INVALID_VERDICT"
