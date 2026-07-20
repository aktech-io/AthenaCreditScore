from __future__ import annotations

"""
Model card generation (NemoScore Phase 3 — model governance).

Every training run (mlops/trainer.py) renders a markdown model card and logs
it to the MLflow run as `model_card.md`, so each registered model version
carries its own documentation pack: OOT metrics, a calibration table, the
training-label mix (real LMS outcomes vs loans.status heuristic), the full
feature list with monotone constraints, SHAP top features, and a fairness
review placeholder for the human promotion step (SR 11-7).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple


def calibration_table(y_true, y_prob, bins: int = 10) -> List[Dict[str, float]]:
    """
    Decile calibration table on the held-out test set: for each predicted-PD
    bin, the mean predicted PD vs the observed default rate.
    """
    import numpy as np

    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if len(y_true) == 0:
        return []

    edges = np.unique(np.quantile(y_prob, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:  # degenerate: single predicted value
        return [{
            "bin_low": float(edges[0]), "bin_high": float(edges[0]),
            "n": int(len(y_true)),
            "mean_predicted": float(y_prob.mean()),
            "observed_rate": float(y_true.mean()),
        }]

    idx = np.clip(np.digitize(y_prob, edges[1:-1], right=True), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        mask = idx == b
        if not mask.any():
            continue
        rows.append({
            "bin_low": float(edges[b]),
            "bin_high": float(edges[b + 1]),
            "n": int(mask.sum()),
            "mean_predicted": float(y_prob[mask].mean()),
            "observed_rate": float(y_true[mask].mean()),
        })
    return rows


def _direction_label(direction: int) -> str:
    return {1: "+1 (pushes PD up)", -1: "-1 (pushes PD down)"}.get(
        direction, "0 (unconstrained)"
    )


def render_model_card(
    *,
    model_name: str,
    register_as: str,
    run_id: str,
    split_kind: str,
    n_train: int,
    n_valid: int,
    n_test: int,
    metrics: Dict[str, float],
    calibration: List[Dict[str, float]],
    feature_names: Sequence[str],
    monotone_directions: Dict[str, int],
    shap_top: List[Tuple[str, float]],
    label_mix: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    trained_at: Optional[datetime] = None,
) -> str:
    """Render the model card as markdown."""
    trained_at = trained_at or datetime.now(timezone.utc)
    lines: List[str] = []
    add = lines.append

    add(f"# Model Card — {model_name} (`{register_as}`)")
    add("")
    add(f"- **MLflow run:** `{run_id}`")
    add(f"- **Trained at:** {trained_at.strftime('%Y-%m-%d %H:%M UTC')}")
    add(f"- **Registered as:** `{register_as}` — promotion to champion is a "
        "separate human-approved step (SR 11-7).")
    add(f"- **Split:** {split_kind} — train {n_train} / valid {n_valid} / test {n_test}")
    add("")

    add("## Intended use")
    add("")
    add("Probability-of-default estimation for NemoScore credit scoring "
        "(PDO-calibrated 300–850 scores, Kenyan market). Not for use outside "
        "credit decisioning; adverse-action reason codes derive from this "
        "model's SHAP attributions.")
    add("")

    add("## Training labels")
    add("")
    if label_mix:
        n_real = int(label_mix.get("n_real_labels", 0))
        n_heur = int(label_mix.get("n_heuristic", 0))
        total = n_real + n_heur
        pct = (100.0 * n_real / total) if total else 0.0
        add(f"| Source | Rows |")
        add(f"|---|---|")
        add(f"| Real LMS repayment outcomes (`training_labels`) | {n_real} |")
        add(f"| `loans.status` heuristic fallback | {n_heur} |")
        add("")
        add(f"{pct:.1f}% of labels come from observed LMS loan outcomes.")
    else:
        add("Label mix not recorded for this run (all labels from the "
            "`loans.status` heuristic).")
    add("")

    add("## Performance (held-out test set)")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    for k, v in metrics.items():
        add(f"| {k} | {v} |")
    add("")

    add("## Calibration (test set, calibrated PD)")
    add("")
    if calibration:
        add("| Bin | n | Mean predicted PD | Observed default rate |")
        add("|---|---|---|---|")
        for row in calibration:
            add(
                f"| {row['bin_low']:.4f}–{row['bin_high']:.4f} | {row['n']} "
                f"| {row['mean_predicted']:.4f} | {row['observed_rate']:.4f} |"
            )
    else:
        add("_No calibration rows (empty test set)._")
    add("")

    add("## Features and monotone constraints")
    add("")
    add("| Feature | Constraint |")
    add("|---|---|")
    for name in feature_names:
        add(f"| {name} | {_direction_label(monotone_directions.get(name, 0))} |")
    add("")

    add("## Top features (mean |SHAP|, test set)")
    add("")
    if shap_top:
        add("| Feature | Mean abs SHAP |")
        add("|---|---|")
        for name, value in shap_top:
            add(f"| {name} | {value:.6f} |")
    else:
        add("_SHAP summary unavailable for this run._")
    add("")

    if params:
        add("## Training parameters")
        add("")
        add("| Param | Value |")
        add("|---|---|")
        for k in sorted(params):
            add(f"| {k} | `{params[k]}` |")
        add("")

    add("## Fairness")
    add("")
    add("> **Placeholder — required before champion promotion.** Disparate-"
        "impact analysis across protected segments (gender, age band, region) "
        "has not yet been run for this version. The reviewer promoting this "
        "model must attach segment-level approval-rate and calibration "
        "comparisons, per the NemoScore governance checklist "
        "(docs/nemoscore-audit.md §6 Phase 3).")
    add("")

    add("## Limitations")
    add("")
    add("- Feature vectors are as-of-now snapshots, not as-of-application; "
        "historical labels can carry temporal leakage until scoring-time "
        "snapshots ship.")
    add("- Real-outcome labels only cover loans whose lifecycle events reached "
        "the LMS exchange; heuristic labels inherit seeded-data bias.")
    add("")
    return "\n".join(lines)
