from __future__ import annotations

"""
Feature-level PSI monitoring (NemoScore Phase 3 — model governance).

At training time mlops/trainer.py snapshots the per-feature training
distribution (decile bin edges + proportions) and logs it to the MLflow run
as `feature_baseline.json`. The weekly drift loop (feedback/loop.py) loads
that baseline from the champion (falling back to challenger) model version,
computes PSI per feature against the last-30-days `lgbm_features` vectors,
exposes each value on the existing `athena_psi_value{feature_name=...}`
Prometheus gauge, and persists rows to `psi_monitoring`.
"""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

BASELINE_ARTIFACT = "feature_baseline.json"
PSI_BUCKETS = 10
_MIN_FLOOR = 1e-4


def compute_baseline(X, buckets: int = PSI_BUCKETS) -> Dict[str, Any]:
    """
    Snapshot the training distribution of every numeric feature in X
    (a pandas DataFrame): decile bin edges + the proportion of training rows
    in each bin. (Near-)constant features are recorded with their value so
    drift away from that value is still detectable.
    """
    import numpy as np

    baseline: Dict[str, Any] = {}
    for col in X.columns:
        vals = np.asarray(X[col], dtype=float)
        vals = vals[~np.isnan(vals)]
        if len(vals) == 0:
            continue
        edges = np.unique(np.percentile(vals, np.linspace(0, 100, buckets + 1)))
        if len(edges) < 2:
            baseline[col] = {"constant": float(edges[0])}
            continue
        counts, _ = np.histogram(vals, bins=edges)
        # np.histogram's last bin is closed on the right, so all values land.
        proportions = counts / counts.sum()
        baseline[col] = {
            "bin_edges": [float(e) for e in edges],
            "proportions": [float(p) for p in proportions],
        }
    return baseline


def psi_from_baseline(entry: Dict[str, Any], values: List[float]) -> Optional[float]:
    """
    PSI of `values` against one feature's baseline entry. Returns None when
    it cannot be computed (no data / degenerate baseline).
    """
    import numpy as np

    vals = np.asarray(values, dtype=float)
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return None

    if "constant" in entry:
        # Training saw a single value: PSI proxy = share of current rows that
        # moved away from it, mapped through the standard PSI term.
        moved = float(np.mean(np.abs(vals - entry["constant"]) > 1e-12))
        base = np.array([1.0 - _MIN_FLOOR, _MIN_FLOOR])
        cur = np.clip(np.array([1.0 - moved, moved]), _MIN_FLOOR, None)
        cur = cur / cur.sum()
        return float(np.sum((cur - base) * np.log(cur / base)))

    edges = np.asarray(entry["bin_edges"], dtype=float)
    base_pcts = np.asarray(entry["proportions"], dtype=float)
    # Open the outermost bins so out-of-range current values still count.
    edges = edges.copy()
    edges[0] = -np.inf
    edges[-1] = np.inf
    cur_counts, _ = np.histogram(vals, bins=edges)
    cur_pcts = cur_counts / cur_counts.sum()

    base_pcts = np.where(base_pcts < _MIN_FLOOR, _MIN_FLOOR, base_pcts)
    cur_pcts = np.where(cur_pcts < _MIN_FLOOR, _MIN_FLOOR, cur_pcts)
    return float(np.sum((cur_pcts - base_pcts) * np.log(cur_pcts / base_pcts)))


def compute_feature_psi(
    baseline: Dict[str, Any], current: Dict[str, List[float]]
) -> Dict[str, float]:
    """PSI per feature; features missing from either side are skipped."""
    out: Dict[str, float] = {}
    for name, entry in baseline.items():
        values = current.get(name)
        if not values:
            continue
        psi = psi_from_baseline(entry, values)
        if psi is not None:
            out[name] = round(psi, 6)
    return out


def set_feature_psi_gauges(psi_by_feature: Dict[str, float]) -> None:
    from monitoring.metrics import PSI_GAUGE

    for name, value in psi_by_feature.items():
        PSI_GAUGE.labels(feature_name=name).set(value)


def load_training_baseline(aliases: tuple = ("champion", "challenger")) -> Optional[Dict[str, Any]]:
    """
    Load feature_baseline.json from the MLflow run behind the champion model
    version (falling back to challenger). Returns None when unavailable —
    callers must treat feature PSI as best-effort.
    """
    import mlflow

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    model_name = os.getenv("MLFLOW_MODEL_NAME", "AthenaScorer")
    client = mlflow.tracking.MlflowClient()
    for alias in aliases:
        try:
            mv = client.get_model_version_by_alias(model_name, alias)
            with tempfile.TemporaryDirectory() as tmpdir:
                local = mlflow.artifacts.download_artifacts(
                    run_id=mv.run_id, artifact_path=BASELINE_ARTIFACT, dst_path=tmpdir
                )
                with open(local) as fh:
                    baseline = json.load(fh)
            logger.info(
                "Feature PSI baseline loaded",
                alias=alias, model=model_name, n_features=len(baseline),
            )
            return baseline
        except Exception as exc:
            logger.info(
                "No feature baseline for alias",
                alias=alias, model=model_name, error=str(exc),
            )
    return None
