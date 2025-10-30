from aiauto.suites.drift.run_evidently import compute_drift

def test_drift_gate_placeholder():
    report = compute_drift("datasets/train.parquet", "datasets/eval.parquet")
    assert report["feature_drift_rate"] <= 0.10
