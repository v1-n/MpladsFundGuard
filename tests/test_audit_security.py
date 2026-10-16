import pytest
from pathlib import Path
from backend.app.services.audit_service import AuditService
from backend.app.schemas.audit import AuditReviewSubmission
from backend.app.core.auth import AuthenticatedReviewer

AUTH_HEADER_ALPHA = {"Authorization": "Bearer auditor-test-token"}
AUTH_HEADER_BETA = {"Authorization": "Bearer auditor-beta-token"}
AUTH_HEADER_ADMIN = {"Authorization": "Bearer lead-admin-token"}


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
        # Explicit check that verdicts, scores, ranks, and cohorts never leak into the blind sample
        assert "audit_verdict" not in item
        assert "auditor_notes" not in item
        assert "cohort" not in item
        assert "anomaly_score" not in item
        assert "rank" not in item


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
    for path in [
        "/api/v1/audit/key",
        "/api/v1/audit/sample/key",
        "/api/v1/key",
        "/data/clean/manual_audit_sample_key.csv",
    ]:
        res = client.get(path)
        assert res.status_code in [404, 405]


def test_audit_review_unauthorized_access_rejected(client):
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]

    payload = {
        "work_id": work_id,
        "verdict": "Normal / Regular",
        "notes": "Unauthenticated test submission",
    }

    # 1. POST without auth header rejected with 401
    submit_res = client.post("/api/v1/audit/reviews", json=payload)
    assert submit_res.status_code == 401
    assert submit_res.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. GET without auth header rejected with 401
    get_res = client.get("/api/v1/audit/reviews")
    assert get_res.status_code == 401
    assert get_res.json()["error"]["code"] == "UNAUTHORIZED"

    # 3. Request with forged / invalid token rejected with 401
    invalid_header = {"Authorization": "Bearer totally-fake-token-xyz"}
    invalid_res = client.post("/api/v1/audit/reviews", json=payload, headers=invalid_header)
    assert invalid_res.status_code == 401
    assert invalid_res.json()["error"]["code"] == "INVALID_TOKEN"


def test_audit_review_reviewer_impersonation_prevented(client):
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]

    # Authenticated as Alpha, but attempting to forge reviewer_id as Beta
    forged_payload = {
        "work_id": work_id,
        "reviewer_id": "Auditor-Test-Beta",
        "verdict": "Normal / Regular",
        "notes": "Attempting to submit as another reviewer",
    }
    res = client.post("/api/v1/audit/reviews", json=forged_payload, headers=AUTH_HEADER_ALPHA)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_IMPERSONATION"


def test_audit_review_cross_reviewer_data_access_prevented(client):
    # Auditor Alpha cannot snoop on Auditor Beta's reviews
    res = client.get("/api/v1/audit/reviews?reviewer_id=Auditor-Test-Beta", headers=AUTH_HEADER_ALPHA)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_ACCESS"


def test_audit_review_persistence_workflow(client):
    # 1. Fetch first sample work ID
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]

    # 2. Submit a review with session authentication
    payload = {
        "work_id": work_id,
        "verdict": "Normal / Regular",
        "notes": "Verified completion photo on portal dashboard.",
    }
    submit_res = client.post("/api/v1/audit/reviews", json=payload, headers=AUTH_HEADER_ALPHA)
    assert submit_res.status_code == 201
    record = submit_res.json()["data"]
    assert record["work_id"] == work_id
    assert record["reviewer_id"] == "Auditor-Test-Alpha"
    assert record["verdict"] == "Normal / Regular"
    assert "updated_at" in record

    # 3. Retrieve own reviews
    get_res = client.get("/api/v1/audit/reviews", headers=AUTH_HEADER_ALPHA)
    assert get_res.status_code == 200
    reviews = get_res.json()["data"]["reviews"]
    assert len(reviews) >= 1
    found = [r for r in reviews if r["work_id"] == work_id]
    assert len(found) == 1
    assert found[0]["verdict"] == "Normal / Regular"
    assert found[0]["reviewer_id"] == "Auditor-Test-Alpha"


def test_audit_review_admin_access(client):
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]

    # Submit review as Alpha
    client.post(
        "/api/v1/audit/reviews",
        json={"work_id": work_id, "verdict": "Normal / Regular", "notes": "Alpha note"},
        headers=AUTH_HEADER_ALPHA,
    )

    # Lead-Auditor (admin) can list all reviews and filter by reviewer
    admin_res = client.get("/api/v1/audit/reviews", headers=AUTH_HEADER_ADMIN)
    assert admin_res.status_code == 200
    reviews = admin_res.json()["data"]["reviews"]
    assert len(reviews) >= 1

    # Lead-Auditor can filter specifically for Alpha
    admin_filter_res = client.get("/api/v1/audit/reviews?reviewer_id=Auditor-Test-Alpha", headers=AUTH_HEADER_ADMIN)
    assert admin_filter_res.status_code == 200
    alpha_reviews = admin_filter_res.json()["data"]["reviews"]
    for r in alpha_reviews:
        assert r["reviewer_id"] == "Auditor-Test-Alpha"


def test_audit_review_duplicate_submission_upserts(client):
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]

    # First submission
    p1 = {"work_id": work_id, "verdict": "Normal / Regular", "notes": "Initial assessment"}
    r1 = client.post("/api/v1/audit/reviews", json=p1, headers=AUTH_HEADER_ALPHA)
    assert r1.status_code == 201

    # Second submission for same work_id and reviewer
    p2 = {"work_id": work_id, "verdict": "Inefficient / Incomplete", "notes": "Revised after deeper portal inspection"}
    r2 = client.post("/api/v1/audit/reviews", json=p2, headers=AUTH_HEADER_ALPHA)
    assert r2.status_code == 201
    rec2 = r2.json()["data"]
    assert rec2["verdict"] == "Inefficient / Incomplete"
    assert rec2["notes"] == "Revised after deeper portal inspection"

    # Confirm there is only ONE record for this work and reviewer
    get_res = client.get("/api/v1/audit/reviews", headers=AUTH_HEADER_ALPHA)
    matching = [r for r in get_res.json()["data"]["reviews"] if r["work_id"] == work_id]
    assert len(matching) == 1
    assert matching[0]["verdict"] == "Inefficient / Incomplete"


def test_audit_review_invalid_verdict_rejected(client):
    sample_res = client.get("/api/v1/audit/sample")
    work_id = sample_res.json()["data"]["sample"][0]["work_id"]

    payload = {
        "work_id": work_id,
        "verdict": "Totally Fraudulent Verdict Not Allowed",
        "notes": "Invalid verdict",
    }
    submit_res = client.post("/api/v1/audit/reviews", json=payload, headers=AUTH_HEADER_ALPHA)
    assert submit_res.status_code == 400
    err = submit_res.json()
    assert err["error"]["code"] == "INVALID_VERDICT"


def test_audit_review_sqlite_persistence_across_restarts(tmp_path):
    # Verify that SQLite database retains data when AuditService is restarted
    db_file = tmp_path / "test_persistence.db"

    # Instance 1
    service_1 = AuditService(db_path=db_file)
    sample_df = service_1.repo.get_blind_audit_sample_df()
    sample_work_id = str(sample_df["Work ID"].iloc[0])

    reviewer_alpha = AuthenticatedReviewer(reviewer_id="Auditor-Restart-Test", role="reviewer")
    submission = AuditReviewSubmission(
        work_id=sample_work_id,
        verdict="Normal / Regular",
        notes="Testing durable SQLite transactions across restarts",
    )
    service_1.submit_review(submission, authenticated_reviewer=reviewer_alpha)

    # Instance 2 (simulating app restart with new process/instance pointing to same DB)
    service_2 = AuditService(db_path=db_file)
    retrieved = service_2.get_reviews(authenticated_reviewer=reviewer_alpha)

    assert retrieved.total_reviews == 1
    record = retrieved.reviews[0]
    assert record.work_id == sample_work_id
    assert record.reviewer_id == "Auditor-Restart-Test"
    assert record.verdict == "Normal / Regular"
    assert record.notes == "Testing durable SQLite transactions across restarts"
