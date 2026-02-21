from __future__ import annotations

"""
MLflow Client — thin async-friendly wrapper around the MLflow tracking/registry APIs.

Responsibilities:
  - Log experiment runs (metrics, params, artifacts)
  - Promote / demote models between staging, champion, and challenger aliases
  - List available versions for the current champion and challenger
  - Compare champion vs challenger metrics to decide promotion
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import mlflow
import mlflow.lightgbm
from mlflow import MlflowClient
import structlog

logger = structlog.get_logger(__name__)

MLFLOW_URI   = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
EXPERIMENT   = os.getenv("MLFLOW_EXPERIMENT_NAME", "athena_credit_scoring")
REGISTERED_MODEL = "athena_lgbm_scorer"

# MLflow model aliases (used to resolve champion/challenger at inference)
ALIAS_CHAMPION   = "champion"
ALIAS_CHALLENGER = "challenger"
ALIAS_STAGING    = "staging"

mlflow.set_tracking_uri(MLFLOW_URI)


def get_client() -> MlflowClient:
    return MlflowClient(tracking_uri=MLFLOW_URI)


def ensure_experiment() -> str:
    """Return experiment ID, creating if necessary."""
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    if exp is None:
        exp_id = mlflow.create_experiment(EXPERIMENT)
        logger.info("MLflow experiment created", name=EXPERIMENT, id=exp_id)
        return exp_id
    return exp.experiment_id


def start_run(run_name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager: start an MLflow run under the Athena experiment."""
    exp_id = ensure_experiment()
    return mlflow.start_run(experiment_id=exp_id, run_name=run_name, tags=tags or {})


def log_metrics(metrics: Dict[str, float], step: Optional[int] = None) -> None:
    mlflow.log_metrics(metrics, step=step)


def log_params(params: Dict[str, Any]) -> None:
    # MLflow requires all param values to be strings
    mlflow.log_params({k: str(v) for k, v in params.items()})


def log_artifact(local_path: str) -> None:
    mlflow.log_artifact(local_path)


def register_model(run_id: str, artifact_path: str = "lgbm_model") -> str:
    """
    Register a model version from the given run under REGISTERED_MODEL.
    Returns the new model version string.
    """
    model_uri = f"runs:/{run_id}/{artifact_path}"
    result = mlflow.register_model(model_uri=model_uri, name=REGISTERED_MODEL)
    version = result.version
    logger.info("Model registered", model=REGISTERED_MODEL, version=version, run_id=run_id)
    return version


def promote_to_staging(version: str) -> None:
    """Tag a version as staging (ready for evaluation)."""
    client = get_client()
    client.set_registered_model_alias(REGISTERED_MODEL, ALIAS_STAGING, version)
    logger.info("Model promoted to staging", version=version)


def promote_to_challenger(version: str) -> None:
    """Promote a staging version to challenger (receives CHALLENGER_TRAFFIC_PCT traffic)."""
    client = get_client()
    client.set_registered_model_alias(REGISTERED_MODEL, ALIAS_CHALLENGER, version)
    logger.info("Model promoted to challenger", version=version)


def promote_challenger_to_champion() -> Optional[str]:
    """
    Demote the current champion to archived, promote the challenger to champion.
    Returns the version that became champion, or None if no challenger is set.
    """
    client = get_client()
    try:
        challenger_mv = client.get_model_version_by_alias(REGISTERED_MODEL, ALIAS_CHALLENGER)
        champion_mv   = client.get_model_version_by_alias(REGISTERED_MODEL, ALIAS_CHAMPION)

        logger.info(
            "Promoting challenger to champion",
            new_champion=challenger_mv.version,
            old_champion=champion_mv.version,
        )
        # Archive old champion
        client.delete_registered_model_alias(REGISTERED_MODEL, ALIAS_CHAMPION)
        client.set_model_version_tag(REGISTERED_MODEL, champion_mv.version, "retired", "true")

        # Elevate challenger
        client.set_registered_model_alias(REGISTERED_MODEL, ALIAS_CHAMPION, challenger_mv.version)
        client.delete_registered_model_alias(REGISTERED_MODEL, ALIAS_CHALLENGER)

        return challenger_mv.version
    except mlflow.exceptions.MlflowException as e:
        logger.warning("Promotion failed", error=str(e))
        return None


def get_champion_version() -> Optional[str]:
    """Return the current champion model version string."""
    try:
        mv = get_client().get_model_version_by_alias(REGISTERED_MODEL, ALIAS_CHAMPION)
        return mv.version
    except Exception:
        return None


def get_challenger_version() -> Optional[str]:
    """Return the current challenger model version string, or None."""
    try:
        mv = get_client().get_model_version_by_alias(REGISTERED_MODEL, ALIAS_CHALLENGER)
        return mv.version
    except Exception:
        return None


def compare_champion_challenger() -> Dict[str, Any]:
    """
    Pull the latest metrics from champion and challenger runs.
    Returns a comparison dict with the recommendation (promote/keep/rollback).
    """
    client = get_client()

    def _get_metrics(alias: str) -> Tuple[Optional[str], Dict[str, float]]:
        try:
            mv = client.get_model_version_by_alias(REGISTERED_MODEL, alias)
            run = client.get_run(mv.run_id)
            return mv.version, run.data.metrics
        except Exception:
            return None, {}

    champ_ver, champ_metrics  = _get_metrics(ALIAS_CHAMPION)
    chall_ver, chall_metrics  = _get_metrics(ALIAS_CHALLENGER)

    champ_ks = champ_metrics.get("ks_statistic", -1)
    chall_ks = chall_metrics.get("ks_statistic", -1)
    champ_auc = champ_metrics.get("roc_auc", -1)
    chall_auc = chall_metrics.get("roc_auc", -1)

    ks_improvement  = chall_ks  - champ_ks  if champ_ks  > 0 else 0
    auc_improvement = chall_auc - champ_auc if champ_auc > 0 else 0

    recommendation = "keep_champion"
    if ks_improvement >= 0.02 or auc_improvement >= 0.005:
        recommendation = "promote_challenger"
    elif ks_improvement <= -0.03 or auc_improvement <= -0.01:
        recommendation = "rollback_challenger"

    return {
        "champion":  {"version": champ_ver, "ks": champ_ks,  "auc": champ_auc},
        "challenger": {"version": chall_ver, "ks": chall_ks, "auc": chall_auc},
        "ks_improvement": round(ks_improvement, 4),
        "auc_improvement": round(auc_improvement, 4),
        "recommendation": recommendation,
    }


def list_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """Return the most recent experiment runs with their key metrics."""
    exp_id = ensure_experiment()
    runs = mlflow.search_runs(
        experiment_ids=[exp_id],
        order_by=["start_time DESC"],
        max_results=limit,
    )
    results = []
    for _, row in runs.iterrows():
        results.append({
            "run_id":   row.get("run_id"),
            "run_name": row.get("tags.mlflow.runName"),
            "status":   row.get("status"),
            "ks":       row.get("metrics.ks_statistic"),
            "auc":      row.get("metrics.roc_auc"),
            "start":    str(row.get("start_time")),
        })
    return results
