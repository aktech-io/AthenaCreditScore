from __future__ import annotations

"""
Phase 4 decisioning endpoints (contract: docs/nemoscore-api.yaml 1.4.0):

  POST /api/v1/credit-score/{customer_id}/affordability
  GET  /api/v1/credit-score/{customer_id}/pricing

Affordability = DTI assessment against income/obligations (provided by the
caller, or estimated from M-Pesa features / transactions / repayments).
Pricing = risk-based flat monthly rate + graduated limit ladder from the
latest persisted score+PD. Thin files (INSUFFICIENT_DATA) are never priced
automatically — the pricing endpoint returns 409 so the LMS routes them to
manual review.
"""

from dataclasses import asdict
from statistics import mean
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.scoring import _check_access
from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db
from scoring import pricing
from scoring.pdo_transformer import PDOTransformer

router = APIRouter()
_pdo = PDOTransformer()

INCOME_LOOKBACK_DAYS = 180
OBLIGATION_LOOKBACK_DAYS = 90


# ── Shared: latest usable score event ───────────────────────────────────────

async def _latest_score_event(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    row = await db.execute(text("""
        SELECT final_score, pd_probability, status, scored_at
        FROM credit_score_events WHERE customer_id = :cid
        ORDER BY scored_at DESC LIMIT 1
    """), {"cid": customer_id})
    r = row.fetchone()
    if not r:
        return None
    score = int(float(r[0])) if r[0] is not None else None
    pd_prob = float(r[1]) if r[1] is not None else None
    if pd_prob is None and score is not None:
        # Legacy events pre-date pd persistence — invert the PDO transform.
        pd_prob = _pdo.pd_from_score(score)
    return {"score": score, "pd": pd_prob, "status": r[2], "scored_at": str(r[3])}


# ── GET /credit-score/{id}/pricing ──────────────────────────────────────────

@router.get("/credit-score/{customer_id}/pricing")
async def get_pricing(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Risk-based pricing from the latest persisted score + PD. Added in 1.4.0."""
    _check_access(claims, customer_id)

    event = await _latest_score_event(db, customer_id)
    if event is None or event["score"] is None:
        raise HTTPException(status_code=404, detail="No score found for customer — score first")
    if event["status"] == "INSUFFICIENT_DATA":
        raise HTTPException(
            status_code=409,
            detail="Latest score is INSUFFICIENT_DATA — thin files must not be "
                   "priced automatically; route to manual review",
        )

    closed_row = await db.execute(text("""
        SELECT count(*) FROM loans
        WHERE customer_id = :cid AND status = 'CLOSED'
    """), {"cid": customer_id})
    closed_loans = int(closed_row.scalar() or 0)

    rate = pricing.risk_adjusted_rate(event["score"], event["pd"])
    limit = pricing.limit_for(event["score"], closed_loans)

    return {
        "customer_id": customer_id,
        "currency": "KES",
        "rate_type": "FLAT_MONTHLY",
        "final_score": event["score"],
        "score_band": rate.band,
        "pd_probability": round(event["pd"], 6),
        "scored_at": event["scored_at"],
        "rate": {
            "base_monthly_rate": rate.base_monthly_rate,
            "risk_premium_monthly": rate.risk_premium_monthly,
            "monthly_rate": rate.monthly_rate,
            "capped": rate.capped,
            "lgd": rate.lgd,
        },
        "limit": asdict(limit),
        "rate_band_table": pricing.rate_bands(),
        "first_time_limit_table": pricing.first_time_limits(),
    }


# ── POST /credit-score/{id}/affordability ───────────────────────────────────

class AffordabilityRequest(BaseModel):
    requested_amount: float = Field(gt=0, description="Loan principal, KES")
    term_months: int = Field(ge=1, le=60)
    monthly_income: Optional[float] = Field(
        default=None, ge=0,
        description="Gross monthly income (KES). Estimated from M-Pesa "
                    "features / transactions when omitted.")
    existing_monthly_obligations: Optional[float] = Field(
        default=None, ge=0,
        description="Existing monthly debt service (KES). Estimated from "
                    "recent repayments when omitted.")


async def _estimate_income(db: AsyncSession, customer_id: int) -> tuple[float, str]:
    """(income, source) — M-Pesa cash-flow features first, then transaction
    credits over the last 180 days. Raises 422 when neither exists."""
    try:
        from features.pipeline import get_or_compute_features
        features = await get_or_compute_features(db, customer_id)
    except Exception:
        features = None
    if features and float(features.get("has_mpesa_data") or 0) >= 1 \
            and float(features.get("mpesa_monthly_inflow_avg") or 0) > 0:
        return float(features["mpesa_monthly_inflow_avg"]), "MPESA_STATEMENTS"

    rows = await db.execute(text("""
        SELECT to_char(transaction_date, 'YYYY-MM') AS m, SUM(amount)
        FROM transactions
        WHERE customer_id = :cid AND UPPER(transaction_type) = 'CREDIT'
          AND transaction_date >= CURRENT_DATE - CAST(:days AS integer)
        GROUP BY 1
    """), {"cid": customer_id, "days": INCOME_LOOKBACK_DAYS})
    monthly = [float(r[1]) for r in rows.fetchall()]
    if monthly:
        return round(mean(monthly), 2), "TRANSACTIONS_180D"

    raise HTTPException(
        status_code=422,
        detail="monthly_income not provided and cannot be estimated — no "
               "M-Pesa statement data or credit transactions on record",
    )


async def _estimate_obligations(db: AsyncSession, customer_id: int) -> tuple[float, str]:
    """(obligations, source) — average monthly debt service from repayments
    over the last 90 days. No repayments → 0 (legitimately unlevered)."""
    row = await db.execute(text("""
        SELECT COALESCE(SUM(amount_paid), 0) FROM repayments
        WHERE customer_id = :cid
          AND payment_date >= CURRENT_DATE - CAST(:days AS integer)
    """), {"cid": customer_id, "days": OBLIGATION_LOOKBACK_DAYS})
    total = float(row.scalar() or 0)
    if total > 0:
        return round(total / (OBLIGATION_LOOKBACK_DAYS / 30.0), 2), "REPAYMENTS_90D"
    return 0.0, "NONE_OBSERVED"


@router.post("/credit-score/{customer_id}/affordability")
async def post_affordability(
    customer_id: int,
    body: AffordabilityRequest,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Affordability / DTI assessment for a requested loan. Added in 1.4.0."""
    _check_access(claims, customer_id)

    if body.monthly_income is not None:
        income, income_source = float(body.monthly_income), "PROVIDED"
    else:
        income, income_source = await _estimate_income(db, customer_id)

    if body.existing_monthly_obligations is not None:
        obligations, obligations_source = float(body.existing_monthly_obligations), "PROVIDED"
    else:
        obligations, obligations_source = await _estimate_obligations(db, customer_id)

    # Rate: risk-based when a usable score exists; otherwise the conservative
    # Poor-band base rate (affordability is still meaningful without a score —
    # pricing itself is what 409s on thin files).
    event = await _latest_score_event(db, customer_id)
    if event and event["score"] is not None and event["status"] != "INSUFFICIENT_DATA":
        rate = pricing.risk_adjusted_rate(event["score"], event["pd"])
        monthly_rate, rate_source = rate.monthly_rate, "RISK_BASED"
        score_band: Optional[str] = rate.band
    else:
        monthly_rate = pricing.rate_bands()["Poor"]
        rate_source, score_band = "DEFAULT_POOR_BAND", None

    result = pricing.assess_affordability(
        monthly_income=income,
        existing_monthly_obligations=obligations,
        requested_amount=body.requested_amount,
        term_months=body.term_months,
        monthly_rate=monthly_rate,
    )

    return {
        "customer_id": customer_id,
        "currency": "KES",
        "rate_type": "FLAT_MONTHLY",
        "income_source": income_source,
        "obligations_source": obligations_source,
        "rate_source": rate_source,
        "score_band": score_band,
        **asdict(result),
    }
