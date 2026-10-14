def test_model_evaluation_endpoint(client):
    response = client.get("/api/v1/model-evaluation")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "meta" in res
    assert "disclaimer" in res["meta"]
    
    data = res["data"]
    assert "cohort_sizes" in data
    assert data["cohort_sizes"]["completed_works"] == 36989
    assert data["cohort_sizes"]["in_progress_works"] == 21061
    
    assert "seed_stability" in data
    assert data["seed_stability"]["Completed"]["jaccard_index"] == 0.9355
    assert data["seed_stability"]["In-Progress"]["jaccard_index"] == 0.9672
    
    assert "synthetic_benchmark" in data
    bench = data["synthetic_benchmark"]
    assert bench["isolation_forest"]["roc_auc_mean"] > 0.85
    assert bench["robust_z_score"]["roc_auc_mean"] > 0.75
    
    assert "limitations" in data
    assert "Screening scores reflect relative multi-dimensional extremity" in data["limitations"]
