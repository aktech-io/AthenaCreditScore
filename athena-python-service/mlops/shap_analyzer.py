from __future__ import annotations

"""
SHAP Analyzer — post-hoc explainability on recent default outcomes.

Responsibilities:
  1. Load recent defaulted loans with their feature vectors from the feature store.
  2. Compute SHAP values using the current champion model.
  3. Aggregate into a DataFrame of mean |SHAP| per feature (global importance).
  4. Identify the top-K features driving defaults.
  5. Log results to MLflow and persist to the `shap_logs` table.
  6. Return a ranked list of features with explanations for the feedback loop.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

TOP_K_FEATURES = 10


async def analyse_recent_defaults(
    db,                            # AsyncSession
    lookback_days: int = 90,
    model_target: str = "champion",
) -> Dict[str, Any]:
    """
    Main entry point. Pulls recent default feature vectors, runs SHAP,
    logs to MLflow, persists results, and returns ranked feature importances.

    Args:
        db:            SQLAlchemy AsyncSession
        lookback_days: window over which to collect defaults
        model_target:  'champion' or 'challenger'

    Returns:
        {
          "feature_importances": [{"feature": str, "mean_abs_shap": float}, ...],
          "n_defaults_analysed": int,
          "top_drivers": [str],
          "analysis_date": str,
        }
    """
    from sqlalchemy import text

    since = date.today() - timedelta(days=lookback_days)

    # ── 1. Load recent defaults with their feature vectors ────────────────────
    rows = await db.execute(text("""
        SELECT
            cse.customer_id,
            fv.feature_vector
        FROM credit_score_events cse
        JOIN loans l          ON l.score_event_id = cse.event_id
        JOIN feature_values fv ON fv.customer_id = cse.customer_id
        JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
        WHERE l.status = 'DEFAULT'
          AND cse.scored_at >= :since
          AND fd.feature_set_name = 'lgbm_features'
        ORDER BY cse.scored_at DESC
        LIMIT 500
    """), {"since": since})
    records = rows.fetchall()

    if len(records) < 10:
        logger.info("Not enough defaults for SHAP analysis", count=len(records))
        return {
            "feature_importances": [],
            "n_defaults_analysed": len(records),
            "top_drivers": [],
            "analysis_date": str(date.today()),
        }

    logger.info("Loaded defaults for SHAP", count=len(records))

    # ── 2. Build feature matrix ───────────────────────────────────────────────
    feature_dicts = [
        json.loads(r[1]) if isinstance(r[1], str) else r[1]
        for r in records
    ]
    # Align columns across all records
    all_keys = sorted({k for d in feature_dicts for k in d if not k.startswith("_")})
    X = np.array([
        [float(d.get(k, 0)) for k in all_keys]
        for d in feature_dicts
    ])

    # ── 3. Load model and compute SHAP ────────────────────────────────────────
    shap_values, model_version = _compute_shap(X, model_target, all_keys)

    if shap_values is None:
        logger.warning("SHAP computation failed — model not available")
        return {
            "feature_importances": [],
            "n_defaults_analysed": len(records),
            "top_drivers": [],
            "analysis_date": str(date.today()),
        }

    # ── 4. Aggregate: mean |SHAP| per feature ────────────────────────────────
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    ranked = sorted(
        zip(all_keys, mean_abs_shap.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )
    feature_importances = [
        {"feature": f, "mean_abs_shap": round(v, 6)}
        for f, v in ranked
    ]
    top_drivers = [fi["feature"] for fi in feature_importances[:TOP_K_FEATURES]]

    # ── 5. Log to MLflow ──────────────────────────────────────────────────────
    try:
        import mlflow
        from mlops.mlflow_client import MLFLOW_URI, EXPERIMENT, ensure_experiment
        mlflow.set_tracking_uri(MLFLOW_URI)
        exp_id = ensure_experiment()
        with mlflow.start_run(experiment_id=exp_id, run_name=f"shap_analysis_{date.today()}"):
            for fi in feature_importances[:TOP_K_FEATURES]:
                mlflow.log_metric(f"shap_{fi['feature']}", fi["mean_abs_shap"])
            mlflow.log_param("n_defaults", len(records))
            mlflow.log_param("analysis_date", str(date.today()))
    except Exception as e:
        logger.warning("MLflow SHAP logging failed", error=str(e))

    # ── 6. Persist to shap_logs ───────────────────────────────────────────────
    from sqlalchemy import text as t
    try:
        await db.execute(t("""
            INSERT INTO shap_logs
                (model_version, analysis_date, feature_importances, n_samples, top_drivers)
            VALUES
                (:mv, :dt, :fi::jsonb, :n, :td::jsonb)
            ON CONFLICT (model_version, analysis_date)
            DO UPDATE SET
                feature_importances = EXCLUDED.feature_importances,
                n_samples = EXCLUDED.n_samples,
                top_drivers = EXCLUDED.top_drivers
        """), {
            "mv": model_version or "unknown",
            "dt": date.today(),
            "fi": json.dumps(feature_importances),
            "n":  len(records),
            "td": json.dumps(top_drivers),
        })
        await db.commit()
    except Exception as e:
        logger.warning("SHAP log persistence failed", error=str(e))

    logger.info(
        "SHAP analysis complete",
        n_defaults=len(records),
        top_feature=top_drivers[0] if top_drivers else None,
    )

    return {
        "feature_importances": feature_importances,
        "n_defaults_analysed": len(records),
        "top_drivers": top_drivers,
        "analysis_date": str(date.today()),
    }


def _compute_shap(
    X: np.ndarray,
    model_target: str,
    feature_names: List[str],
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Load the LightGBM model from MLflow and compute SHAP values.
    Returns (shap_values array, model_version_string) or (None, None) on failure.
    """
    try:
        import mlflow
        from mlflow import MlflowClient
        from mlops.mlflow_client import REGISTERED_MODEL, MLFLOW_URI
        import lightgbm as lgb
        import shap

        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient(tracking_uri=MLFLOW_URI)

        alias = model_target  # 'champion' or 'challenger'
        mv = client.get_model_version_by_alias(REGISTERED_MODEL, alias)
        model_uri = f"models:/{REGISTERED_MODEL}@{alias}"
        model = mlflow.lightgbm.load_model(model_uri)
        version = mv.version

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # For binary classification, shap returns [class0, class1] — take class 1 (default)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        return shap_values, version

    except Exception as exc:
        logger.error("SHAP model load failed", error=str(exc))
        return None, None
