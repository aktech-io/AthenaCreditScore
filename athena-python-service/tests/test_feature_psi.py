"""
Tests for monitoring/feature_psi.py — training baseline snapshot and
feature-level PSI computation.
"""
import numpy as np
import pandas as pd

from monitoring.feature_psi import (
    compute_baseline,
    compute_feature_psi,
    psi_from_baseline,
)

rng = np.random.default_rng(42)


def make_train_frame(n=1000):
    return pd.DataFrame({
        "bureau_score": rng.normal(620, 60, n),
        "payment_cv": rng.gamma(2.0, 0.15, n),
        "has_mpesa_data": np.zeros(n),  # constant in training
    })


class TestComputeBaseline:
    def test_baseline_shape(self):
        base = compute_baseline(make_train_frame())
        assert set(base) == {"bureau_score", "payment_cv", "has_mpesa_data"}
        entry = base["bureau_score"]
        assert len(entry["bin_edges"]) == 11
        assert len(entry["proportions"]) == 10
        assert abs(sum(entry["proportions"]) - 1.0) < 1e-9

    def test_constant_feature_recorded_as_constant(self):
        base = compute_baseline(make_train_frame())
        assert base["has_mpesa_data"] == {"constant": 0.0}

    def test_json_roundtrippable(self):
        import json
        base = compute_baseline(make_train_frame())
        assert compute_feature_psi(json.loads(json.dumps(base)), {
            "bureau_score": list(rng.normal(620, 60, 500)),
        })


class TestPsi:
    def test_same_distribution_is_stable(self):
        base = compute_baseline(make_train_frame())
        current = list(rng.normal(620, 60, 800))
        psi = psi_from_baseline(base["bureau_score"], current)
        assert psi < 0.05

    def test_shifted_distribution_alerts(self):
        base = compute_baseline(make_train_frame())
        current = list(rng.normal(500, 60, 800))  # 2-sigma mean shift
        psi = psi_from_baseline(base["bureau_score"], current)
        assert psi > 0.2

    def test_out_of_range_values_still_counted(self):
        base = compute_baseline(make_train_frame())
        psi = psi_from_baseline(base["bureau_score"], [10_000.0] * 100)
        assert psi > 1.0

    def test_constant_feature_no_drift(self):
        base = compute_baseline(make_train_frame())
        psi = psi_from_baseline(base["has_mpesa_data"], [0.0] * 200)
        assert psi is not None and psi < 0.01

    def test_constant_feature_drift_detected(self):
        base = compute_baseline(make_train_frame())
        # Half the recent population now has M-Pesa data.
        psi = psi_from_baseline(base["has_mpesa_data"], [0.0] * 100 + [1.0] * 100)
        assert psi > 0.2

    def test_empty_current_returns_none(self):
        base = compute_baseline(make_train_frame())
        assert psi_from_baseline(base["bureau_score"], []) is None


class TestComputeFeaturePsi:
    def test_skips_features_missing_from_current(self):
        base = compute_baseline(make_train_frame())
        out = compute_feature_psi(base, {"bureau_score": list(rng.normal(620, 60, 300))})
        assert "bureau_score" in out
        assert "payment_cv" not in out

    def test_ignores_unknown_current_features(self):
        base = compute_baseline(make_train_frame())
        out = compute_feature_psi(base, {"brand_new_feature": [1.0, 2.0]})
        assert out == {}
