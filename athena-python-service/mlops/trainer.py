from __future__ import annotations

import os
import json
import tempfile
from typing import Optional

import joblib
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import shap
import structlog
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

logger = structlog.get_logger(__name__)

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "athena-credit-scorer")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "AthenaScorer")

# Domain monotone constraints: +1 = feature can only push PD up, -1 = only
# down, 0 = unconstrained (direction genuinely ambiguous). Guards against
# implausible attributions (e.g. a high bureau score raising PD) that noisy
# or synthetic labels would otherwise let the trees learn — adverse-action
# reason codes derive from SHAP, so directions must be defensible.
MONOTONE_DIRECTIONS = {
    "avg_loan_spacing_days": -1,
    "max_delinquency_streak": 1,
    "delinquency_rate_90d": 1,
    "payment_cv": 1,
    "early_repayment_rate": -1,
    "capital_growth_rate": -1,
    "profit_margin": -1,
    "bureau_score": -1,
    "open_npa_accounts": 1,
    "mpesa_monthly_inflow_avg": -1,
    "mpesa_inflow_cv": 1,
    "mpesa_income_regularity": -1,
    "mpesa_outflow_inflow_ratio": 1,
    "mpesa_low_balance_rate": 1,
    "mpesa_merchant_diversity": -1,
    "mpesa_betting_ratio": 1,
    "mpesa_savings_ratio": -1,
    "mpesa_fuliza_draw_count": 1,
}


def ks_statistic(y_true, y_prob) -> float:
    """Compute Kolmogorov-Smirnov statistic — key metric for credit models."""
    from scipy.stats import ks_2samp
    pos_probs = [p for p, y in zip(y_prob, y_true) if y == 1]
    neg_probs = [p for p, y in zip(y_prob, y_true) if y == 0]
    if not pos_probs or not neg_probs:
        return 0.0
    stat, _ = ks_2samp(pos_probs, neg_probs)
    return float(stat)


def _three_way_split(X: pd.DataFrame, y: pd.Series, time_col: Optional[str]):
    """
    Split into train / valid (early stopping + calibration) / test.

    With a time column the test set is strictly out-of-time (most recent 20%),
    which is the credit-model standard: performance must hold on a later
    period, not a random shuffle of the same one. Without a time column we
    fall back to stratified random splits.
    """
    if time_col and time_col in X.columns:
        order = X[time_col].argsort(kind="stable")
        X_sorted = X.iloc[order].drop(columns=[time_col])
        y_sorted = y.iloc[order]
        n = len(X_sorted)
        test_start = int(n * 0.8)
        valid_start = int(n * 0.6)
        return (
            X_sorted.iloc[:valid_start], y_sorted.iloc[:valid_start],
            X_sorted.iloc[valid_start:test_start], y_sorted.iloc[valid_start:test_start],
            X_sorted.iloc[test_start:], y_sorted.iloc[test_start:],
            "out_of_time",
        )

    X_rest, X_test, y_rest, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_valid, y_train, y_valid = train_test_split(
        X_rest, y_rest, test_size=0.25, random_state=42, stratify=y_rest
    )
    return X_train, y_train, X_valid, y_valid, X_test, y_test, "random_stratified"


def train_and_register(
    features_df: pd.DataFrame,
    target_col: str = "default_flag",
    register_as: str = "challenger",
    run_name: Optional[str] = None,
    time_col: Optional[str] = "scored_at_ts",
    label_mix: Optional[dict] = None,
) -> str:
    """
    Train a LightGBM credit scoring model with an out-of-time test set and
    isotonic probability calibration, log everything to MLflow, and register
    it in the model registry.

    Governance note: this NEVER promotes to champion. New versions are
    registered under the `register_as` alias (challenger by default) and
    promotion is a separate, human-approved step.

    Returns the MLflow run_id.
    """
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    X = features_df.drop(columns=[target_col])
    y = features_df[target_col]

    X_train, y_train, X_valid, y_valid, X_test, y_test, split_kind = _three_way_split(
        X, y, time_col
    )

    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": 6,
        "min_child_samples": 20,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "n_estimators": 500,
        "verbose": -1,
        "class_weight": "balanced",
        "monotone_constraints": [
            MONOTONE_DIRECTIONS.get(c, 0) for c in X_train.columns
        ],
        "monotone_constraints_method": "advanced",
    }

    with mlflow.start_run(run_name=run_name or f"athena-lgbm-{register_as}") as run:
        mlflow.log_params(params)
        mlflow.log_param("split_kind", split_kind)
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_param("n_valid", len(X_valid))
        mlflow.log_param("n_test", len(X_test))
        # Label provenance: real LMS repayment outcomes vs loans.status heuristic.
        if label_mix:
            mlflow.log_param("n_real_labels", int(label_mix.get("n_real_labels", 0)))
            mlflow.log_param("n_heuristic_labels", int(label_mix.get("n_heuristic", 0)))

        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_valid, y_valid)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        # ── Calibration: isotonic fit on the validation set ──────────────────
        valid_prob_raw = model.predict_proba(X_valid)[:, 1]
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(valid_prob_raw, y_valid)

        # ── Metrics on the held-out (OOT) test set ───────────────────────────
        y_prob_raw = model.predict_proba(X_test)[:, 1]
        y_prob_cal = calibrator.predict(y_prob_raw)
        y_pred = (y_prob_cal > 0.5).astype(int)

        metrics = {
            "auc_roc": round(roc_auc_score(y_test, y_prob_raw), 4),
            "ks_statistic": round(ks_statistic(y_test.tolist(), y_prob_raw.tolist()), 4),
            "pr_auc": round(average_precision_score(y_test, y_prob_raw), 4),
            "f1_score": round(f1_score(y_test, y_pred), 4),
            "brier_raw": round(brier_score_loss(y_test, y_prob_raw), 4),
            "brier_calibrated": round(brier_score_loss(y_test, y_prob_cal), 4),
        }
        mlflow.log_metrics(metrics)
        logger.info("Training metrics (OOT test)", split=split_kind, **metrics)

        # ── SHAP feature importance ──────────────────────────────────────────
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        shap_dict = dict(zip(X_test.columns.tolist(), mean_abs_shap.tolist()))
        top_features = sorted(shap_dict.items(), key=lambda kv: -kv[1])[:10]
        mlflow.log_param("shap_top_features", json.dumps(top_features[:5]))

        # ── Governance artifacts: PSI baseline + model card ──────────────────
        from mlops.model_card import calibration_table, render_model_card
        from monitoring.feature_psi import BASELINE_ARTIFACT, compute_baseline

        feature_baseline = compute_baseline(X_train)
        card_md = render_model_card(
            model_name=MODEL_NAME,
            register_as=register_as,
            run_id=run.info.run_id,
            split_kind=split_kind,
            n_train=len(X_train), n_valid=len(X_valid), n_test=len(X_test),
            metrics=metrics,
            calibration=calibration_table(y_test.tolist(), y_prob_cal.tolist()),
            feature_names=X_train.columns.tolist(),
            monotone_directions=MONOTONE_DIRECTIONS,
            shap_top=top_features,
            label_mix=label_mix,
            params={k: v for k, v in params.items() if k != "monotone_constraints"},
        )

        # ── Log calibrator + model, register ─────────────────────────────────
        with tempfile.TemporaryDirectory() as tmpdir:
            cal_path = os.path.join(tmpdir, "calibrator.joblib")
            joblib.dump(calibrator, cal_path)
            mlflow.log_artifact(cal_path)

            baseline_path = os.path.join(tmpdir, BASELINE_ARTIFACT)
            with open(baseline_path, "w") as fh:
                json.dump(feature_baseline, fh)
            mlflow.log_artifact(baseline_path)

            card_path = os.path.join(tmpdir, "model_card.md")
            with open(card_path, "w") as fh:
                fh.write(card_md)
            mlflow.log_artifact(card_path)

        mlflow.lightgbm.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )
        run_id = run.info.run_id

    # Point the alias (challenger by default) at the new version so the
    # scorer can load it. Champion promotion is a separate human-approved step.
    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    new_version = next(v.version for v in versions if v.run_id == run_id)
    client.set_registered_model_alias(MODEL_NAME, register_as, new_version)
    logger.info("Model registered", run_id=run_id, version=new_version, alias=register_as)

    return run_id
