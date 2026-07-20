from __future__ import annotations

"""
Risk-based pricing + affordability math for NemoScore Phase 4 (pure logic —
no DB, no I/O; the API layer in api/decisioning.py wires it to data).

Kenyan digital-lending conventions:
- Amounts in KES.
- Rates are FLAT MONTHLY rates (interest charged on the original principal
  each month), the dominant convention for mobile/digital lenders in Kenya —
  NOT reducing-balance APRs. total repayable = P * (1 + r * term).
- Limits are small and ladder up with demonstrated repayment (count of prior
  CLOSED loans), the standard first-time-borrower graduation model.

All tables/caps are env-overridable; defaults documented in
docs/nemoscore-api.yaml (1.4.0).
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

from scoring.pdo_transformer import PDOTransformer

# ── Configuration (env-overridable) ─────────────────────────────────────────

#: Base flat monthly rate per score band (before the PD-driven premium).
_DEFAULT_RATE_BANDS: Dict[str, float] = {
    "Excellent": 0.030,
    "Very Good": 0.040,
    "Good":      0.055,
    "Fair":      0.070,
    "Marginal":  0.090,
    "Poor":      0.120,
}

#: First-time borrower limit (KES) per score band.
_DEFAULT_FIRST_LIMITS: Dict[str, float] = {
    "Excellent": 50_000.0,
    "Very Good": 30_000.0,
    "Good":      20_000.0,
    "Fair":      10_000.0,
    "Marginal":   5_000.0,
    "Poor":       2_000.0,
}


def _env_json(name: str, default: Dict[str, float]) -> Dict[str, float]:
    raw = os.getenv(name)
    if not raw:
        return dict(default)
    try:
        parsed = json.loads(raw)
        merged = dict(default)
        merged.update({k: float(v) for k, v in parsed.items()})
        return merged
    except (ValueError, TypeError, AttributeError):
        return dict(default)


def rate_bands() -> Dict[str, float]:
    """Band → base flat monthly rate. Override: PRICING_RATE_BANDS (JSON)."""
    return _env_json("PRICING_RATE_BANDS", _DEFAULT_RATE_BANDS)


def first_time_limits() -> Dict[str, float]:
    """Band → first-time limit in KES. Override: PRICING_FIRST_LIMITS (JSON)."""
    return _env_json("PRICING_FIRST_LIMITS", _DEFAULT_FIRST_LIMITS)


def lgd() -> float:
    """Loss given default for unsecured digital loans. Override: PRICING_LGD."""
    return float(os.getenv("PRICING_LGD", "0.55"))


def max_monthly_rate() -> float:
    """Hard cap on the risk-adjusted flat monthly rate. Override: PRICING_MAX_MONTHLY_RATE."""
    return float(os.getenv("PRICING_MAX_MONTHLY_RATE", "0.15"))


def repeat_step() -> float:
    """Limit multiplier increment per prior CLOSED loan. Override: PRICING_REPEAT_STEP."""
    return float(os.getenv("PRICING_REPEAT_STEP", "0.5"))


def repeat_max_steps() -> int:
    """Cap on ladder steps counted. Override: PRICING_REPEAT_MAX_STEPS."""
    return int(os.getenv("PRICING_REPEAT_MAX_STEPS", "6"))


def pti_cap() -> float:
    """Max total-debt-service-to-income ratio for AFFORDABLE. Override: AFFORDABILITY_PTI_CAP."""
    return float(os.getenv("AFFORDABILITY_PTI_CAP", "0.40"))


def stretch_cap() -> float:
    """DTI ceiling for STRETCHED (above → UNAFFORDABLE). Override: AFFORDABILITY_STRETCH_CAP."""
    return float(os.getenv("AFFORDABILITY_STRETCH_CAP", "0.50"))


# ── Band normalisation ──────────────────────────────────────────────────────

def band_for_score(score: int) -> str:
    """Canonical band label derived from the score (ignores legacy stored
    labels like VERY_POOR — the score is the source of truth)."""
    return PDOTransformer._get_band(int(score))


# ── Rate ────────────────────────────────────────────────────────────────────

@dataclass
class RiskRate:
    band: str
    base_monthly_rate: float
    risk_premium_monthly: float   # PD-driven expected-loss premium
    monthly_rate: float           # base + premium, capped
    capped: bool
    lgd: float


def risk_adjusted_rate(score: int, pd_probability: float) -> RiskRate:
    """
    Expected-loss-adjusted flat monthly rate:
        rate = base_rate(band) + (PD * LGD) / 12
    The premium spreads the annualized expected loss (PD × LGD) over 12
    monthly charges; the result is capped at PRICING_MAX_MONTHLY_RATE.
    """
    band = band_for_score(score)
    base = rate_bands()[band]
    premium = round(max(0.0, float(pd_probability)) * lgd() / 12.0, 6)
    raw = base + premium
    cap = max_monthly_rate()
    return RiskRate(
        band=band,
        base_monthly_rate=base,
        risk_premium_monthly=premium,
        monthly_rate=round(min(raw, cap), 6),
        capped=raw > cap,
        lgd=lgd(),
    )


# ── Limit ladder ────────────────────────────────────────────────────────────

@dataclass
class LimitDecision:
    borrower_type: str            # FIRST_TIME | REPEAT
    closed_loans: int
    base_limit: float             # first-time limit for the band
    multiplier: float             # 1 + step * min(closed, max_steps)
    max_loan_amount: float


def limit_for(score: int, closed_loans: int) -> LimitDecision:
    """Graduated limit ladder: first-time borrowers start at the band's base
    limit; each prior CLOSED loan adds `repeat_step` to the multiplier, up to
    `repeat_max_steps` steps."""
    band = band_for_score(score)
    base = first_time_limits()[band]
    steps = min(max(0, int(closed_loans)), repeat_max_steps())
    multiplier = 1.0 + repeat_step() * steps
    return LimitDecision(
        borrower_type="REPEAT" if closed_loans > 0 else "FIRST_TIME",
        closed_loans=int(closed_loans),
        base_limit=base,
        multiplier=round(multiplier, 2),
        max_loan_amount=round(base * multiplier, 2),
    )


# ── Installment math (flat monthly rate) ────────────────────────────────────

def flat_monthly_installment(principal: float, monthly_rate: float, term_months: int) -> float:
    """Flat-rate installment: principal/term + interest on original principal.
    total repayable = P * (1 + r * term)."""
    if term_months <= 0:
        raise ValueError("term_months must be >= 1")
    return round(principal * (1.0 / term_months + monthly_rate), 2)


def max_principal_for_installment(installment: float, monthly_rate: float, term_months: int) -> float:
    """Inverse of flat_monthly_installment."""
    if term_months <= 0:
        raise ValueError("term_months must be >= 1")
    if installment <= 0:
        return 0.0
    return round(installment / (1.0 / term_months + monthly_rate), 2)


# ── Affordability / DTI ─────────────────────────────────────────────────────

@dataclass
class AffordabilityResult:
    monthly_income: float
    existing_monthly_obligations: float
    requested_amount: float
    term_months: int
    monthly_rate: float
    monthly_installment: float
    total_repayable: float
    dti_current: Optional[float]        # obligations / income (None if income <= 0)
    dti_with_loan: Optional[float]      # (obligations + installment) / income
    disposable_income_after_loan: float
    pti_cap: float
    max_affordable_installment: float   # pti_cap * income - obligations, floored at 0
    max_loan_amount: float              # principal whose installment == max affordable
    decision: str                       # AFFORDABLE | STRETCHED | UNAFFORDABLE


def assess_affordability(
    monthly_income: float,
    existing_monthly_obligations: float,
    requested_amount: float,
    term_months: int,
    monthly_rate: float,
) -> AffordabilityResult:
    """
    DTI here is total monthly debt service (existing obligations + the new
    installment) over gross monthly income. Decision:
        dti_with_loan <= pti_cap       → AFFORDABLE
        dti_with_loan <= stretch_cap   → STRETCHED
        otherwise (or income <= 0)     → UNAFFORDABLE
    """
    income = max(0.0, float(monthly_income))
    obligations = max(0.0, float(existing_monthly_obligations))
    installment = flat_monthly_installment(requested_amount, monthly_rate, term_months)
    total_repayable = round(requested_amount * (1.0 + monthly_rate * term_months), 2)

    cap = pti_cap()
    stretch = stretch_cap()

    if income > 0:
        dti_current = round(obligations / income, 4)
        dti_with_loan = round((obligations + installment) / income, 4)
    else:
        dti_current = None
        dti_with_loan = None

    max_installment = round(max(0.0, cap * income - obligations), 2)
    max_loan = max_principal_for_installment(max_installment, monthly_rate, term_months)

    if dti_with_loan is None:
        decision = "UNAFFORDABLE"
    elif dti_with_loan <= cap:
        decision = "AFFORDABLE"
    elif dti_with_loan <= stretch:
        decision = "STRETCHED"
    else:
        decision = "UNAFFORDABLE"

    return AffordabilityResult(
        monthly_income=round(income, 2),
        existing_monthly_obligations=round(obligations, 2),
        requested_amount=round(float(requested_amount), 2),
        term_months=int(term_months),
        monthly_rate=monthly_rate,
        monthly_installment=installment,
        total_repayable=total_repayable,
        dti_current=dti_current,
        dti_with_loan=dti_with_loan,
        disposable_income_after_loan=round(income - obligations - installment, 2),
        pti_cap=cap,
        max_affordable_installment=max_installment,
        max_loan_amount=max_loan,
        decision=decision,
    )
