from __future__ import annotations

"""
Collections-priority score for the LMS collections-service (NemoScore Phase 4,
contract 1.5.0). Pure logic — no DB, no I/O; api/collections.py wires it.

Ranks delinquent cases by where collections effort pays off, not just by DPD.
Components (sum = 0–100, higher = work this case first):

  risk       0–30  borrower PD (the model's view of default risk)
  exposure   0–30  outstanding amount, saturating — twice the money is more
                   urgent, but not twice as urgent forever
  urgency    0–25  DPD curve peaking in the 31–90 roll-rate-prevention window;
                   very early cases often self-cure, very late ones belong to
                   legal/write-off, mid-stage is where a call changes outcomes
  behaviour  0–10  promise-to-pay track record (broken PTPs raise priority —
                   a willingness problem needs escalation; kept promises lower it)
  ability    0–5   cash-flow ability to pay from M-Pesa features — a delinquent
                   borrower with healthy inflows is the most recoverable case

The band mapping matches the LMS CasePriority enum exactly
(LOW / NORMAL / HIGH / CRITICAL) so the collections-service can assign the
response band directly. When the API 404s/409s (no score / thin file) the LMS
keeps its existing DPD-threshold rules — fail-closed to current behaviour.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

ABILITY_STRONG = "STRONG"
ABILITY_WEAK = "WEAK"
ABILITY_UNKNOWN = "UNKNOWN"

#: LMS CasePriority values, in escalation order.
PRIORITY_BANDS = ["LOW", "NORMAL", "HIGH", "CRITICAL"]


def exposure_ref() -> float:
    """Outstanding amount (KES) that earns half the exposure weight.
    Override: COLLECTIONS_EXPOSURE_REF."""
    return float(os.getenv("COLLECTIONS_EXPOSURE_REF", "50000"))


def band_cutoffs() -> Dict[str, float]:
    """Score cutoffs for CRITICAL/HIGH/NORMAL (below NORMAL → LOW).
    Override: COLLECTIONS_CUTOFF_CRITICAL / _HIGH / _NORMAL."""
    return {
        "CRITICAL": float(os.getenv("COLLECTIONS_CUTOFF_CRITICAL", "70")),
        "HIGH": float(os.getenv("COLLECTIONS_CUTOFF_HIGH", "50")),
        "NORMAL": float(os.getenv("COLLECTIONS_CUTOFF_NORMAL", "25")),
    }


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ── Components ──────────────────────────────────────────────────────────────

def risk_component(pd_probability: float) -> float:
    """0–30: linear in PD."""
    return round(30.0 * _clamp(float(pd_probability), 0.0, 1.0), 2)


def exposure_component(outstanding_amount: float) -> float:
    """0–30: saturating ratio outstanding/(outstanding+ref); ref KES earns 15."""
    amt = max(0.0, float(outstanding_amount))
    ref = exposure_ref()
    return round(30.0 * amt / (amt + ref), 2) if amt > 0 else 0.0


def urgency_component(dpd: int) -> float:
    """0–25: DPD curve. Peak at 61–90 (roll-rate prevention); declines past 180
    where recovery odds drop and the case belongs to legal/write-off review."""
    d = max(0, int(dpd))
    if d == 0:
        return 0.0
    if d <= 7:
        return 8.0
    if d <= 30:
        return 15.0
    if d <= 60:
        return 22.0
    if d <= 90:
        return 25.0
    if d <= 180:
        return 18.0
    return 10.0


def behaviour_component(broken_ptp_count: int, fulfilled_ptp_count: int) -> float:
    """0–10: base 5, +2.5 per broken promise (cap 2), −2.5 per kept one (cap 2)."""
    broken = min(2, max(0, int(broken_ptp_count)))
    fulfilled = min(2, max(0, int(fulfilled_ptp_count)))
    return round(_clamp(5.0 + 2.5 * broken - 2.5 * fulfilled, 0.0, 10.0), 2)


def ability_to_pay(features: Optional[Dict[str, Any]]) -> str:
    """STRONG / WEAK / UNKNOWN from M-Pesa cash-flow features (12-mo lookback)."""
    if not features or float(features.get("has_mpesa_data") or 0) < 1:
        return ABILITY_UNKNOWN
    inflow = float(features.get("mpesa_monthly_inflow_avg") or 0)
    low_balance = float(features.get("mpesa_low_balance_rate") or 0)
    if inflow <= 0 or low_balance > 0.7:
        return ABILITY_WEAK
    if low_balance <= 0.3:
        return ABILITY_STRONG
    return ABILITY_UNKNOWN


def ability_component(ability: str) -> float:
    """0–5: strong payers are the most recoverable delinquents — prioritize."""
    return {ABILITY_STRONG: 5.0, ABILITY_UNKNOWN: 2.5, ABILITY_WEAK: 1.0}[ability]


# ── Action recommendation ───────────────────────────────────────────────────

def recommended_action(dpd: int, ability: str) -> str:
    """Coarse next-best-action by delinquency stage and ability to pay. The
    collections-service's strategy engine may override; this is the default."""
    d = max(0, int(dpd))
    if d == 0:
        return "NONE"
    if d <= 7:
        return "SOFT_REMINDER" if ability == ABILITY_WEAK else "SELF_CURE_WATCH"
    if d <= 30:
        return "SOFT_REMINDER"
    if d <= 90:
        return "RESTRUCTURE_OFFER" if ability == ABILITY_WEAK else "PRIORITY_CALL"
    if d <= 180:
        return "RESTRUCTURE_OFFER" if ability == ABILITY_WEAK else "FIELD_VISIT"
    return "LEGAL_REVIEW"


# ── Composite ───────────────────────────────────────────────────────────────

@dataclass
class PriorityResult:
    priority_score: float          # 0–100
    priority_band: str             # LOW | NORMAL | HIGH | CRITICAL (LMS enum)
    components: Dict[str, float]
    ability_to_pay: str
    recommended_action: str


def collections_priority(
    pd_probability: float,
    dpd: int,
    outstanding_amount: float,
    broken_ptp_count: int = 0,
    fulfilled_ptp_count: int = 0,
    features: Optional[Dict[str, Any]] = None,
) -> PriorityResult:
    ability = ability_to_pay(features)
    components = {
        "risk": risk_component(pd_probability),
        "exposure": exposure_component(outstanding_amount),
        "urgency": urgency_component(dpd),
        "behaviour": behaviour_component(broken_ptp_count, fulfilled_ptp_count),
        "ability": ability_component(ability),
    }
    score = round(sum(components.values()), 2)

    cutoffs = band_cutoffs()
    if score >= cutoffs["CRITICAL"]:
        band = "CRITICAL"
    elif score >= cutoffs["HIGH"]:
        band = "HIGH"
    elif score >= cutoffs["NORMAL"]:
        band = "NORMAL"
    else:
        band = "LOW"

    return PriorityResult(
        priority_score=score,
        priority_band=band,
        components=components,
        ability_to_pay=ability,
        recommended_action=recommended_action(dpd, ability),
    )
