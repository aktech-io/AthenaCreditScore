from __future__ import annotations

import os
import json
from typing import Optional

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import shap
import structlog
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
from sklearn.model_selection import train_test_split

logger = structlog.get_logger(__name__)

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "athena-credit-scorer")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "AthenaScorer")


def ks_statistic(y_true, y_prob) -> float:
    """Compute Kolmogorov-Smirnov statistic — key metric for credit models."""
    from scipy.stats import ks_2samp
    pos_probs = [p for p, y in zip(y_prob, y_true) if y == 1]
    neg_probs = [p for p, y in zip(y_prob, y_true) if y == 0]
    if not pos_probs or not neg_probs:
        return 0.0
    stat, _ = ks_2samp(pos_probs, neg_probs)
    return float(stat)


def train_and_register(
    features_df: pd.DataFrame,
    target_col: str = "default_flag",
    register_as: str = "challenger",
    run_name: Optional[str] = None,
) -> str:
    """
    Train a LightGBM credit scoring model, log all metrics and artefacts
    to MLflow, and register it in the model registry.

    Returns the MLflow run_id.
    """
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    X = features_df.drop(columns=[target_col])
    y = features_df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
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
        "early_stopping_rounds": 50,
        "verbose": -1,
        "class_weight": "balanced",
    }

    with mlflow.start_run(run_name=run_name or f"athena-lgbm-{register_as}") as run:
        mlflow.log_params(params)

        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob > 0.5).astype(int)

        auc = roc_auc_score(y_test, y_prob)
        ks = ks_statistic(y_test.tolist(), y_prob.tolist())
        pr_auc = average_precision_score(y_test, y_prob)
        f1 = f1_score(y_test, y_pred)

        mlflow.log_metrics({
            "auc_roc": round(auc, 4),
            "ks_statistic": round(ks, 4),
            "pr_auc": round(pr_auc, 4),
            "f1_score": round(f1, 4),
        })
        logger.info("Training metrics", auc=auc, ks=ks, pr_auc=pr_auc)

        # SHAP feature importance
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        shap_dict = dict(zip(X.columns.tolist(), mean_abs_shap.tolist()))
        top_features = sorted(shap_dict.items(), key=lambda kv: -kv[1])[:10]
        # Log top features as a parameter (avoids local disk artifact write during seeding)
        mlflow.log_param("shap_top_features", json.dumps(top_features[:5]))

        # Register model
        mlflow.lightgbm.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )
        run_id = run.info.run_id
        logger.info("Model registered", run_id=run_id, alias=register_as)

    return run_id
