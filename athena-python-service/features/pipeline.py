from __future__ import annotations

"""
Feature pipeline for the LightGBM scorer.

Computes the `lgbm_features` v1 vector per customer from the operational
tables (loans, repayments, crb_reports) and persists it to the feature store,
so `compute_hybrid_score` can use the registered ML model for the PD.

Known v1 limitations (Phase 2 closes these):
- capital_growth_rate / profit_margin default to 0.0 — SME financials are not
  yet captured on the customer record.
- sector_risk_modifier defaults to 1.0 — no sector on the customer record yet.
- Vectors are as-of-now, not as-of-application; training joins must treat
  them accordingly (temporal leakage risk on historical labels).
"""

import json
from datetime import date
from statistics import mean, stdev
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from features.feature_store import read_features, register_definition, write_features

logger = structlog.get_logger(__name__)

LGBM_FEATURE_SET = "lgbm_features"
LGBM_FEATURE_VERSION = "1"

# Must match the training frame / registered model feature names.
FEATURE_NAMES = [
    "avg_loan_spacing_days",
    "max_delinquency_streak",
    "delinquency_rate_90d",
    "total_loans",
    "payment_cv",
    "early_repayment_rate",
    "capital_growth_rate",
    "profit_margin",
    "sector_risk_modifier",
    "bureau_score",
    "open_npa_accounts",
]

_definition_registered = False


async def _ensure_definition(db: AsyncSession) -> None:
    global _definition_registered
    if _definition_registered:
        return
    await register_definition(
        db,
        feature_set_name=LGBM_FEATURE_SET,
        version=LGBM_FEATURE_VERSION,
        feature_names=FEATURE_NAMES,
        description="LightGBM scorer input vector (loan performance + bureau)",
    )
    _definition_registered = True


async def compute_customer_features(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    """
    Compute the lgbm_features v1 vector for one customer.
    Returns None when there is no loan history AND no bureau data — an
    all-defaults vector would be meaningless to the model.
    """
    loan_rows = await db.execute(text("""
        SELECT loan_id, disbursement_date, maturity_date, status
        FROM loans WHERE customer_id = :cid
        ORDER BY disbursement_date NULLS LAST
    """), {"cid": customer_id})
    loans = [dict(r._mapping) for r in loan_rows.fetchall()]

    pmt_rows = await db.execute(text("""
        SELECT loan_id, payment_date, amount_paid, days_late
        FROM repayments WHERE customer_id = :cid
        ORDER BY payment_date
    """), {"cid": customer_id})
    payments = [dict(r._mapping) for r in pmt_rows.fetchall()]

    crb_row = await db.execute(text("""
        SELECT bureau_score, extracted_metrics
        FROM crb_reports WHERE customer_id = :cid
        ORDER BY report_date DESC LIMIT 1
    """), {"cid": customer_id})
    crb = crb_row.fetchone()

    if not loans and not crb:
        return None

    # ── Loan spacing ────────────────────────────────────────────────────────
    disb_dates = sorted(l["disbursement_date"] for l in loans if l["disbursement_date"])
    if len(disb_dates) >= 2:
        spacings = [(disb_dates[i + 1] - disb_dates[i]).days for i in range(len(disb_dates) - 1)]
        avg_spacing = round(mean(spacings), 1)
    else:
        avg_spacing = 0.0

    # ── Delinquency streak + 90d rate ───────────────────────────────────────
    max_streak = cur_streak = 0
    for p in payments:
        if int(p["days_late"] or 0) > 0:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 0

    today = date.today()
    recent = [p for p in payments if p["payment_date"] and (today - p["payment_date"]).days <= 90]
    late_recent = [p for p in recent if int(p["days_late"] or 0) > 0]
    delinquency_rate_90d = round(len(late_recent) / len(recent), 4) if recent else 0.0

    # ── Payment regularity ──────────────────────────────────────────────────
    amounts = [float(p["amount_paid"] or 0) for p in payments]
    if len(amounts) >= 2 and mean(amounts) > 0:
        payment_cv = round(stdev(amounts) / mean(amounts), 4)
    else:
        payment_cv = 0.0

    # ── Early repayment: CLOSED loans whose last payment predates maturity ──
    last_pmt_by_loan: Dict[int, date] = {}
    for p in payments:
        if p["payment_date"]:
            lid = p["loan_id"]
            if lid not in last_pmt_by_loan or p["payment_date"] > last_pmt_by_loan[lid]:
                last_pmt_by_loan[lid] = p["payment_date"]
    closed = [l for l in loans if l["status"] == "CLOSED" and l["maturity_date"]]
    early = [
        l for l in closed
        if last_pmt_by_loan.get(l["loan_id"]) and last_pmt_by_loan[l["loan_id"]] < l["maturity_date"]
    ]
    early_repayment_rate = round(len(early) / len(closed), 4) if closed else 0.0

    # ── Bureau ──────────────────────────────────────────────────────────────
    bureau_score = 0
    open_npa_accounts = 0
    if crb:
        bureau_score = int(crb[0] or 0)
        metrics = crb[1] if isinstance(crb[1], dict) else json.loads(crb[1] or "{}")
        open_npa_accounts = int(metrics.get("npa_count", 0) or 0)

    return {
        "avg_loan_spacing_days": avg_spacing,
        "max_delinquency_streak": max_streak,
        "delinquency_rate_90d": delinquency_rate_90d,
        "total_loans": len(loans),
        "payment_cv": payment_cv,
        "early_repayment_rate": early_repayment_rate,
        "capital_growth_rate": 0.0,      # v1 limitation, see module docstring
        "profit_margin": 0.0,            # v1 limitation
        "sector_risk_modifier": 1.0,     # v1 limitation
        "bureau_score": bureau_score,
        "open_npa_accounts": open_npa_accounts,
    }


async def compute_and_store_features(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    """Compute and persist the vector; returns it (or None if not computable)."""
    features = await compute_customer_features(db, customer_id)
    if features is None:
        return None
    await _ensure_definition(db)
    await write_features(
        db, customer_id, LGBM_FEATURE_SET, LGBM_FEATURE_VERSION, features
    )
    return features


async def get_or_compute_features(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    """Read the latest stored vector; compute and store on miss."""
    stored = await read_features(db, customer_id, LGBM_FEATURE_SET)
    if stored is not None:
        return stored
    return await compute_and_store_features(db, customer_id)


async def recompute_all_features(db: AsyncSession, limit: int = 10_000) -> int:
    """Batch-recompute vectors for every customer with loans or bureau data."""
    rows = await db.execute(text("""
        SELECT DISTINCT c.customer_id FROM customers c
        WHERE EXISTS (SELECT 1 FROM loans l WHERE l.customer_id = c.customer_id)
           OR EXISTS (SELECT 1 FROM crb_reports r WHERE r.customer_id = c.customer_id)
        ORDER BY c.customer_id LIMIT :lim
    """), {"lim": limit})
    ids = [r[0] for r in rows.fetchall()]
    n = 0
    for cid in ids:
        if await compute_and_store_features(db, cid) is not None:
            n += 1
    logger.info("Feature recompute complete", customers=n)
    return n
