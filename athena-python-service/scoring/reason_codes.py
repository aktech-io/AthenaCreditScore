from __future__ import annotations

"""
Deterministic adverse-action reason codes (NemoScore Phase 4).

Every scoring run yields up to TOP_N standardized reason codes explaining what
is holding the score down — ECOA-style adverse-action reasons, EU AI Act
"clear and meaningful explanation". Two derivation paths, matching the PD
source:

- ML path: SHAP contributions from the LightGBM model on the customer's
  feature vector. Features pushing PD *up* (positive SHAP) are adverse;
  the top ones map to standardized codes.
- Scorecard path: scorecard dimension deficits (points lost vs. dimension
  maximum) plus bureau red flags, ranked by severity.

Both paths are fully deterministic for a given input — no LLM involvement.
The LLM's free-text reasoning remains a separate, clearly-labelled overlay.
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

TOP_N = 4

# ── Code registry ────────────────────────────────────────────────────────────
# Codes are stable identifiers; descriptions are customer-safe display text.
REASON_CODES: Dict[str, str] = {
    "NS01": "Non-performing account(s) on credit bureau record",
    "NS02": "Active loan default on credit bureau record",
    "NS03": "Low credit bureau score",
    "NS04": "High recent credit-seeking activity (enquiries or applications)",
    "NS05": "Irregular or unstable income pattern",
    "NS06": "Low average monthly income",
    "NS07": "Low savings relative to income",
    "NS08": "Frequent low account balance events",
    "NS09": "Limited diversity of account activity",
    "NS10": "Recent repayments frequently late",
    "NS11": "Extended run of consecutive late repayments",
    "NS12": "Irregular repayment amounts",
    "NS13": "Limited borrowing history",
    "NS14": "Loans taken in rapid succession",
    "NS15": "Business financial indicators below expectations",
}

# ML-path mapping: lgbm_features name → reason code applied when the feature's
# SHAP contribution pushes PD up. Direction is decided by SHAP, so the code
# text stays neutral about which way the raw value points.
FEATURE_TO_CODE: Dict[str, str] = {
    "open_npa_accounts": "NS01",
    "bureau_score": "NS03",
    "delinquency_rate_90d": "NS10",
    "max_delinquency_streak": "NS11",
    "payment_cv": "NS12",
    "total_loans": "NS13",
    "early_repayment_rate": "NS13",
    "avg_loan_spacing_days": "NS14",
    "capital_growth_rate": "NS15",
    "profit_margin": "NS15",
    "sector_risk_modifier": "NS15",
}

# Scorecard dimension → (code, max points). Deficit fraction ranks severity.
_DIMENSIONS: List[Tuple[str, str, float]] = [
    ("income_stability_score", "NS05", 150.0),
    ("avg_monthly_income_score", "NS06", 150.0),
    ("savings_rate_score", "NS07", 100.0),
    ("low_balance_score", "NS08", 150.0),
    ("transaction_diversity_score", "NS09", 150.0),
]

# Only report a dimension when it lost at least this fraction of its points —
# a near-perfect dimension is not an adverse reason.
_MIN_DEFICIT_FRACTION = 0.25

# SHAP path: ignore contributions below this log-odds magnitude — tiny positive
# attributions on otherwise-clean profiles are model noise, and surfacing them
# as adverse-action reasons misleads the borrower.
_MIN_SHAP_ADVERSE = 0.25


def _entry(code: str) -> Dict[str, str]:
    return {"code": code, "description": REASON_CODES[code]}


def from_shap(shap_contributions: List[Tuple[str, float]]) -> List[Dict[str, str]]:
    """
    Map SHAP contributions (feature_name, shap_value) to reason codes.
    Positive SHAP = pushes PD up = adverse. Deduplicates codes (several
    features can map to one code), keeps most-severe-first ordering.
    """
    adverse = sorted(
        (fs for fs in shap_contributions if fs[1] >= _MIN_SHAP_ADVERSE),
        key=lambda fs: -fs[1],
    )
    seen: set[str] = set()
    out: List[Dict[str, str]] = []
    for feature, _ in adverse:
        code = FEATURE_TO_CODE.get(feature)
        if code and code not in seen:
            seen.add(code)
            out.append(_entry(code))
        if len(out) >= TOP_N:
            break
    return out


def from_scorecard(
    base_result: Any,
    crb_metrics: Optional[Any] = None,
) -> List[Dict[str, str]]:
    """
    Derive reason codes from scorecard dimension deficits and bureau red flags.

    Bureau red flags (hard adverse markers) outrank dimension deficits:
    an active default matters more than a modest savings-rate shortfall.
    """
    ranked: List[Tuple[float, str]] = []  # (severity, code) — higher first

    if crb_metrics is not None:
        if getattr(crb_metrics, "active_defaults", 0) > 0:
            ranked.append((3.0, "NS02"))
        if getattr(crb_metrics, "npa_count", 0) > 0:
            ranked.append((2.9, "NS01"))
        bureau_score = getattr(crb_metrics, "bureau_score", 0)
        if 0 < bureau_score < 550:
            ranked.append((2.5, "NS03"))
        if getattr(crb_metrics, "enquiries_90d", 0) >= 3 or \
           getattr(crb_metrics, "applications_12m", 0) >= 5:
            ranked.append((2.0, "NS04"))

    for attr, code, max_pts in _DIMENSIONS:
        achieved = float(getattr(base_result, attr, 0.0) or 0.0)
        deficit_fraction = (max_pts - achieved) / max_pts
        if deficit_fraction >= _MIN_DEFICIT_FRACTION:
            ranked.append((deficit_fraction, code))

    ranked.sort(key=lambda sc: -sc[0])
    seen: set[str] = set()
    out: List[Dict[str, str]] = []
    for _, code in ranked:
        if code not in seen:
            seen.add(code)
            out.append(_entry(code))
        if len(out) >= TOP_N:
            break
    return out
