from __future__ import annotations

"""
Feature pipeline for the LightGBM scorer.

Computes the `lgbm_features` v2 vector per customer from the operational
tables (loans, repayments, crb_reports, mpesa_transactions) and persists it
to the feature store, so `compute_hybrid_score` can use the registered ML
model for the PD.

v2 (Phase 2) adds 13 M-Pesa cash-flow features computed from ingested
statements (ingestion/mpesa.py) over a 12-month lookback. Customers without
statement data get zero-defaults plus `has_mpesa_data = 0` so the model can
tell "missing" from "truly zero". A model trained on v1 features still works:
scoring/lgbm_scorer.py reindexes the vector to the model's own feature list,
dropping columns it was not trained on.

Remaining limitations:
- capital_growth_rate / profit_margin default to 0.0 — SME financials are not
  yet captured on the customer record.
- sector_risk_modifier defaults to 1.0 — no sector on the customer record yet.
- Vectors are as-of-now, not as-of-application; training joins must treat
  them accordingly (temporal leakage risk on historical labels).
"""

import json
from datetime import date, timedelta
from statistics import mean, stdev
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from features.feature_store import read_features, register_definition, write_features

logger = structlog.get_logger(__name__)

LGBM_FEATURE_SET = "lgbm_features"
LGBM_FEATURE_VERSION = "2"

MPESA_LOOKBACK_DAYS = 365

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
    # v2: M-Pesa cash-flow features (12-month lookback)
    "has_mpesa_data",
    "mpesa_months_observed",
    "mpesa_monthly_inflow_avg",
    "mpesa_inflow_cv",
    "mpesa_income_regularity",
    "mpesa_outflow_inflow_ratio",
    "mpesa_low_balance_rate",
    "mpesa_merchant_diversity",
    "mpesa_airtime_ratio",
    "mpesa_betting_ratio",
    "mpesa_savings_ratio",
    "mpesa_loan_repay_ratio",
    "mpesa_fuliza_draw_count",
]

_MPESA_DEFAULTS: Dict[str, float] = {
    "has_mpesa_data": 0,
    "mpesa_months_observed": 0,
    "mpesa_monthly_inflow_avg": 0.0,
    "mpesa_inflow_cv": 0.0,
    "mpesa_income_regularity": 0.0,
    "mpesa_outflow_inflow_ratio": 0.0,
    "mpesa_low_balance_rate": 0.0,
    "mpesa_merchant_diversity": 0,
    "mpesa_airtime_ratio": 0.0,
    "mpesa_betting_ratio": 0.0,
    "mpesa_savings_ratio": 0.0,
    "mpesa_loan_repay_ratio": 0.0,
    "mpesa_fuliza_draw_count": 0,
}

# Balance below this (KES) at end of a transaction counts as a low-balance
# event — mirrors the "M-Pesa hygiene" thresholds used in cash-flow
# underwriting; deliberately absolute, not income-relative, so it is stable
# across statement lengths.
LOW_BALANCE_KES = 100.0

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
        description="LightGBM scorer input vector (loan performance + bureau + M-Pesa cash flow)",
    )
    _definition_registered = True


async def _compute_mpesa_features(db: AsyncSession, customer_id: int) -> Dict[str, Any]:
    """
    Cash-flow features from ingested M-Pesa statements (12-month lookback).
    Returns _MPESA_DEFAULTS (has_mpesa_data=0) when no statement data exists.
    """
    since = date.today() - timedelta(days=MPESA_LOOKBACK_DAYS)
    rows = await db.execute(text("""
        SELECT txn_time, category, direction, amount, balance, counterparty
        FROM mpesa_transactions
        WHERE customer_id = :cid AND txn_time >= :since
        ORDER BY txn_time
    """), {"cid": customer_id, "since": since})
    return mpesa_features_from_rows([dict(r._mapping) for r in rows.fetchall()])


def mpesa_features_from_rows(txns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure computation over ordered mpesa_transactions rows (also unit-tested)."""
    if not txns:
        return dict(_MPESA_DEFAULTS)

    monthly_inflow: Dict[str, float] = {}
    total_in = total_out = 0.0
    out_by_cat: Dict[str, float] = {}
    merchants = set()
    low_balance = balance_known = 0
    fuliza_draws = 0

    for t in txns:
        amount = float(t["amount"] or 0)
        month = t["txn_time"].strftime("%Y-%m")
        cat = t["category"]
        if t["direction"] == "IN":
            total_in += amount
            # Fuliza draws and savings withdrawals are liquidity moves, not income.
            if cat not in ("FULIZA_DRAW", "SAVINGS_WITHDRAWAL", "LOAN_DISBURSEMENT"):
                monthly_inflow[month] = monthly_inflow.get(month, 0.0) + amount
        else:
            total_out += amount
            out_by_cat[cat] = out_by_cat.get(cat, 0.0) + amount
            if cat in ("PAYBILL", "MERCHANT", "UTILITY") and t["counterparty"]:
                merchants.add(t["counterparty"])
        if cat == "FULIZA_DRAW":
            fuliza_draws += 1
        if t["balance"] is not None:
            balance_known += 1
            if float(t["balance"]) < LOW_BALANCE_KES:
                low_balance += 1

    first, last = txns[0]["txn_time"], txns[-1]["txn_time"]
    months_observed = (last.year - first.year) * 12 + (last.month - first.month) + 1

    inflows = list(monthly_inflow.values())
    inflow_avg = mean(inflows) if inflows else 0.0
    inflow_cv = round(stdev(inflows) / inflow_avg, 4) if len(inflows) >= 2 and inflow_avg > 0 else 0.0

    def out_ratio(*cats: str) -> float:
        return round(sum(out_by_cat.get(c, 0.0) for c in cats) / total_out, 4) if total_out > 0 else 0.0

    return {
        "has_mpesa_data": 1,
        "mpesa_months_observed": months_observed,
        "mpesa_monthly_inflow_avg": round(inflow_avg, 2),
        "mpesa_inflow_cv": inflow_cv,
        "mpesa_income_regularity": round(len(monthly_inflow) / months_observed, 4),
        "mpesa_outflow_inflow_ratio": round(total_out / total_in, 4) if total_in > 0 else 0.0,
        "mpesa_low_balance_rate": round(low_balance / balance_known, 4) if balance_known else 0.0,
        "mpesa_merchant_diversity": len(merchants),
        "mpesa_airtime_ratio": out_ratio("AIRTIME"),
        "mpesa_betting_ratio": out_ratio("BETTING"),
        "mpesa_savings_ratio": out_ratio("SAVINGS_DEPOSIT"),
        "mpesa_loan_repay_ratio": out_ratio("LOAN_REPAYMENT", "FULIZA_REPAY"),
        "mpesa_fuliza_draw_count": fuliza_draws,
    }


async def compute_customer_features(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    """
    Compute the lgbm_features v2 vector for one customer.
    Returns None when there is no loan history, no bureau data AND no M-Pesa
    data — an all-defaults vector would be meaningless to the model.
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

    mpesa = await _compute_mpesa_features(db, customer_id)

    if not loans and not crb and not mpesa["has_mpesa_data"]:
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
        "capital_growth_rate": 0.0,      # see module docstring
        "profit_margin": 0.0,
        "sector_risk_modifier": 1.0,
        "bureau_score": bureau_score,
        "open_npa_accounts": open_npa_accounts,
        **mpesa,
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
           OR EXISTS (SELECT 1 FROM mpesa_transactions m WHERE m.customer_id = c.customer_id)
        ORDER BY c.customer_id LIMIT :lim
    """), {"lim": limit})
    ids = [r[0] for r in rows.fetchall()]
    n = 0
    for cid in ids:
        if await compute_and_store_features(db, cid) is not None:
            n += 1
    logger.info("Feature recompute complete", customers=n)
    return n
