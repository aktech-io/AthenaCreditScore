"""
Tests for mlops/model_card.py — calibration table and model-card rendering.
"""
import numpy as np

from mlops.model_card import calibration_table, render_model_card
from mlops.trainer import MONOTONE_DIRECTIONS

rng = np.random.default_rng(7)


class TestCalibrationTable:
    def test_bins_cover_all_rows(self):
        y_prob = rng.uniform(0, 1, 500)
        y_true = (rng.uniform(0, 1, 500) < y_prob).astype(int)
        rows = calibration_table(y_true, y_prob, bins=10)
        assert sum(r["n"] for r in rows) == 500
        assert len(rows) == 10

    def test_well_calibrated_probs_track_observed(self):
        y_prob = rng.uniform(0, 1, 20_000)
        y_true = (rng.uniform(0, 1, 20_000) < y_prob).astype(int)
        rows = calibration_table(y_true, y_prob, bins=10)
        for r in rows:
            assert abs(r["mean_predicted"] - r["observed_rate"]) < 0.05

    def test_degenerate_single_value(self):
        rows = calibration_table([0, 1, 0, 0], [0.25, 0.25, 0.25, 0.25])
        assert len(rows) == 1
        assert rows[0]["n"] == 4
        assert rows[0]["observed_rate"] == 0.25

    def test_empty_inputs(self):
        assert calibration_table([], []) == []


def render(**overrides):
    kwargs = dict(
        model_name="NemoScorer",
        register_as="challenger",
        run_id="abc123",
        split_kind="out_of_time",
        n_train=600, n_valid=200, n_test=200,
        metrics={"auc_roc": 0.81, "ks_statistic": 0.42, "brier_calibrated": 0.11},
        calibration=[{"bin_low": 0.0, "bin_high": 0.2, "n": 100,
                      "mean_predicted": 0.1, "observed_rate": 0.09}],
        feature_names=["bureau_score", "payment_cv", "total_loans"],
        monotone_directions=MONOTONE_DIRECTIONS,
        shap_top=[("bureau_score", 0.31), ("payment_cv", 0.12)],
        label_mix={"n_real_labels": 150, "n_heuristic": 850},
    )
    kwargs.update(overrides)
    return render_model_card(**kwargs)


class TestRenderModelCard:
    def test_core_sections_present(self):
        card = render()
        for heading in (
            "# Model Card — NemoScorer",
            "## Training labels",
            "## Performance (held-out test set)",
            "## Calibration",
            "## Features and monotone constraints",
            "## Top features",
            "## Fairness",
            "## Limitations",
        ):
            assert heading in card

    def test_metrics_and_run_id_rendered(self):
        card = render()
        assert "`abc123`" in card
        assert "| ks_statistic | 0.42 |" in card

    def test_label_mix_percentage(self):
        card = render()
        assert "| Real LMS repayment outcomes (`training_labels`) | 150 |" in card
        assert "15.0% of labels come from observed LMS loan outcomes." in card

    def test_no_label_mix_notes_heuristic(self):
        card = render(label_mix=None)
        assert "Label mix not recorded" in card

    def test_monotone_directions_rendered(self):
        card = render()
        assert "| bureau_score | -1 (pushes PD down) |" in card
        assert "| payment_cv | +1 (pushes PD up) |" in card
        assert "| total_loans | 0 (unconstrained) |" in card

    def test_fairness_placeholder_blocks_promotion(self):
        card = render()
        assert "Placeholder — required before champion promotion." in card

    def test_calibration_rows_rendered(self):
        card = render()
        assert "| 0.0000–0.2000 | 100 | 0.1000 | 0.0900 |" in card
