from __future__ import annotations

"""
Score simulator delta engine (NemoScore Phase 4) — pure logic, no I/O.

Maps "what-if" deltas onto a COPY of a customer's lgbm_features vector (the
primary, model-backed path) or onto a copy of their transaction list (the
scorecard fallback path used when no feature vector / registered model
exists). Never mutates its inputs — the API layer (api/simulator.py)
guarantees nothing is persisted.

Supported deltas (feature path unless noted):
  clear_delinquencies: true      → max_delinquency_streak = 0,
                                   delinquency_rate_90d = 0, open_npa_accounts = 0
  add_monthly_savings: KES       → raises mpesa_savings_ratio (share of outflow
                                   redirected to savings); fallback: scales down
                                   discretionary debits per month
  reduce_betting_to_zero: true   → mpesa_betting_ratio = 0; fallback: removes
                                   BETTING debits
  close_loans_on_time: n         → total_loans += n, early_repayment_rate blended
                                   toward 1 for the n new on-time closures
  increase_monthly_income: KES   → mpesa_monthly_inflow_avg += KES; fallback:
                                   adds a monthly SALARY credit
  improve_bureau_score: points   → bureau_score += points (feature path only)
  clear_fuliza: true             → mpesa_fuliza_draw_count = 0 (feature path only)
"""

import copy
from typing import Any, Dict, List, Tuple


def _f(features: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = features.get(key, default)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


# ── Feature-vector delta mappings ───────────────────────────────────────────

def _clear_delinquencies(f: Dict[str, Any], _value: Any) -> None:
    f["max_delinquency_streak"] = 0
    f["delinquency_rate_90d"] = 0.0
    f["open_npa_accounts"] = 0


def _add_monthly_savings(f: Dict[str, Any], amount: Any) -> None:
    amount = max(0.0, float(amount))
    inflow = _f(f, "mpesa_monthly_inflow_avg")
    outflow = inflow * _f(f, "mpesa_outflow_inflow_ratio")
    if outflow <= 0:
        # No observed cash flow to redirect — treat the savings as new outflow
        # that is 100% savings on top of a minimal base.
        outflow = amount
    ratio = _f(f, "mpesa_savings_ratio")
    f["mpesa_savings_ratio"] = round(min(1.0, ratio + amount / max(outflow, 1.0)), 4)


def _reduce_betting_to_zero(f: Dict[str, Any], _value: Any) -> None:
    f["mpesa_betting_ratio"] = 0.0


def _close_loans_on_time(f: Dict[str, Any], n: Any) -> None:
    n = max(0, int(n))
    if n == 0:
        return
    total = int(_f(f, "total_loans"))
    early = _f(f, "early_repayment_rate")
    # Blend the existing early-repayment rate with n new on-time closures.
    # (early_repayment_rate is over CLOSED loans; total is a fair proxy weight.)
    weight = max(total, 1)
    f["early_repayment_rate"] = round((early * weight + 1.0 * n) / (weight + n), 4)
    f["total_loans"] = total + n


def _increase_monthly_income(f: Dict[str, Any], amount: Any) -> None:
    amount = max(0.0, float(amount))
    inflow = _f(f, "mpesa_monthly_inflow_avg")
    new_inflow = inflow + amount
    f["mpesa_monthly_inflow_avg"] = round(new_inflow, 2)
    # Same outflow over a larger inflow → the ratio falls proportionally.
    if inflow > 0 and new_inflow > 0:
        f["mpesa_outflow_inflow_ratio"] = round(
            _f(f, "mpesa_outflow_inflow_ratio") * inflow / new_inflow, 4
        )
    if amount > 0 and not int(_f(f, "has_mpesa_data")):
        f["has_mpesa_data"] = 1


def _improve_bureau_score(f: Dict[str, Any], points: Any) -> None:
    f["bureau_score"] = int(min(850, max(0, _f(f, "bureau_score") + int(points))))


def _clear_fuliza(f: Dict[str, Any], _value: Any) -> None:
    f["mpesa_fuliza_draw_count"] = 0


SUPPORTED_DELTAS: Dict[str, Any] = {
    "clear_delinquencies": _clear_delinquencies,
    "add_monthly_savings": _add_monthly_savings,
    "reduce_betting_to_zero": _reduce_betting_to_zero,
    "close_loans_on_time": _close_loans_on_time,
    "increase_monthly_income": _increase_monthly_income,
    "improve_bureau_score": _improve_bureau_score,
    "clear_fuliza": _clear_fuliza,
}

#: Deltas that are boolean switches — falsy values mean "not requested".
_BOOLEAN_DELTAS = {"clear_delinquencies", "reduce_betting_to_zero", "clear_fuliza"}


def normalize_deltas(deltas: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Split the request into (applicable, unknown) delta names; drops falsy
    boolean switches and zero/negative numeric deltas."""
    applicable: Dict[str, Any] = {}
    unknown: List[str] = []
    for name, value in deltas.items():
        if name not in SUPPORTED_DELTAS:
            unknown.append(name)
            continue
        if name in _BOOLEAN_DELTAS:
            if bool(value):
                applicable[name] = True
        else:
            try:
                if float(value) > 0:
                    applicable[name] = value
            except (TypeError, ValueError):
                unknown.append(name)
    return applicable, unknown


def apply_deltas(features: Dict[str, Any], deltas: Dict[str, Any]) -> Dict[str, Any]:
    """Return a NEW feature dict with the (already-normalized) deltas applied.
    The input dict is never mutated."""
    simulated = copy.deepcopy(features)
    for name, value in deltas.items():
        SUPPORTED_DELTAS[name](simulated, value)
    return simulated


# ── Transaction-level fallback (scorecard path) ─────────────────────────────

#: Categories treated as discretionary when scaling debits down for savings.
_DISCRETIONARY = {"BETTING", "ENTERTAINMENT", "AIRTIME", "SHOPPING", "OTHER", "ATM"}

#: Deltas that have no representation in the base scorecard inputs.
FALLBACK_NO_EFFECT = {"clear_delinquencies", "close_loans_on_time",
                      "improve_bureau_score", "clear_fuliza"}


def apply_deltas_to_transactions(
    transactions: List[Dict[str, Any]], deltas: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Fallback mapping onto a COPY of the transaction list for the base
    scorecard. Returns (new_transactions, no_effect_delta_names) — deltas the
    scorecard cannot express are reported, not silently dropped.
    """
    txns = copy.deepcopy(transactions)
    no_effect = [n for n in deltas if n in FALLBACK_NO_EFFECT]

    if deltas.get("reduce_betting_to_zero"):
        txns = [t for t in txns
                if not (str(t.get("transaction_type", "")).upper() == "DEBIT"
                        and str(t.get("category", "")).upper() == "BETTING")]

    if "add_monthly_savings" in deltas:
        target = float(deltas["add_monthly_savings"])
        by_month: Dict[str, float] = {}
        for t in txns:
            if str(t.get("transaction_type", "")).upper() == "DEBIT" \
                    and str(t.get("category", "")).upper() in _DISCRETIONARY \
                    and t.get("transaction_date") is not None:
                mk = t["transaction_date"].strftime("%Y-%m")
                by_month[mk] = by_month.get(mk, 0.0) + float(t.get("amount", 0))
        for t in txns:
            if str(t.get("transaction_type", "")).upper() == "DEBIT" \
                    and str(t.get("category", "")).upper() in _DISCRETIONARY \
                    and t.get("transaction_date") is not None:
                mk = t["transaction_date"].strftime("%Y-%m")
                month_total = by_month.get(mk, 0.0)
                if month_total > 0:
                    scale = max(0.0, 1.0 - target / month_total)
                    t["amount"] = round(float(t.get("amount", 0)) * scale, 2)

    if "increase_monthly_income" in deltas:
        amount = float(deltas["increase_monthly_income"])
        months = sorted({
            t["transaction_date"].strftime("%Y-%m"): t["transaction_date"]
            for t in txns if t.get("transaction_date") is not None
        }.items())
        for _mk, sample_date in months:
            txns.append({
                "transaction_date": sample_date,
                "amount": amount,
                "transaction_type": "CREDIT",
                "category": "SALARY",
                "balance_after": None,
            })

    return txns, no_effect
