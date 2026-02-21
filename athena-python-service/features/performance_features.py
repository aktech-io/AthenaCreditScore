from __future__ import annotations

"""
Performance feature engineering for repeat borrowers.

Computes behavioural signals from historical loan performance:
  - Delinquency streaks (consecutive late/missed payments)
  - Rolling delinquency rate (30/90/180 day windows)
  - Payment regularity coefficient of variation
  - Loan spacing (days between successive loans)
  - Early repayment rate
  - Partial payment ratio

These features are concatenated to the application feature vector
before LightGBM inference.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean, stdev
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceFeatures:
    # Delinquency
    max_delinquency_streak: int = 0          # Longest consecutive late months
    current_delinquency_streak: int = 0      # Ongoing late streak (0 if current)
    total_late_payments: int = 0
    delinquency_rate_30d: float = 0.0        # % of payments late in last 30 days
    delinquency_rate_90d: float = 0.0        # % of payments late in last 90 days
    delinquency_rate_180d: float = 0.0       # % in last 180 days

    # Payment regularity
    payment_cv: float = 0.0                  # CoV of payment amounts (0 = perfectly regular)
    avg_days_late: float = 0.0               # Mean days past due (for late payments only)

    # Loan behaviour
    total_loans: int = 0
    avg_loan_spacing_days: float = 0.0       # Mean days between successive loan start dates
    min_loan_spacing_days: int = 0           # Shortest gap (rapid re-borrowing signal)
    early_repayment_rate: float = 0.0        # Fraction repaid before due date
    partial_payment_rate: float = 0.0        # Fraction with partial payment (<95% due)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def compute_performance_features(
    loan_history: List[Dict[str, Any]],
    payment_history: List[Dict[str, Any]],
    reference_date: Optional[date] = None,
) -> PerformanceFeatures:
    """
    Compute all performance features from loan and payment history.

    Args:
        loan_history: list of dicts with keys:
            loan_id, disbursed_date, due_date, closed_date, status
        payment_history: list of dicts with keys:
            loan_id, due_date, paid_date, amount_due, amount_paid, days_late
        reference_date: the "as-of" date for rolling windows (defaults to today)

    Returns:
        PerformanceFeatures dataclass instance
    """
    ref = reference_date or date.today()
    feats = PerformanceFeatures()

    if not loan_history and not payment_history:
        return feats

    feats.total_loans = len(loan_history)

    # ── Loan spacing ────────────────────────────────────────────────────────
    disbursement_dates = sorted([
        _parse_date(l.get("disbursed_date"))
        for l in loan_history
        if l.get("disbursed_date")
    ])
    if len(disbursement_dates) >= 2:
        spacings = [
            (disbursement_dates[i + 1] - disbursement_dates[i]).days
            for i in range(len(disbursement_dates) - 1)
        ]
        feats.avg_loan_spacing_days = round(mean(spacings), 1)
        feats.min_loan_spacing_days = min(spacings)

    if not payment_history:
        return feats

    # ── Payment windows ─────────────────────────────────────────────────────
    def _in_window(p: Dict, days: int) -> bool:
        due = _parse_date(p.get("due_date"))
        return due is not None and (ref - due).days <= days

    all_pmts = payment_history
    pmts_30  = [p for p in all_pmts if _in_window(p, 30)]
    pmts_90  = [p for p in all_pmts if _in_window(p, 90)]
    pmts_180 = [p for p in all_pmts if _in_window(p, 180)]

    def _late_rate(pmts: List[Dict]) -> float:
        if not pmts:
            return 0.0
        late = sum(1 for p in pmts if (p.get("days_late") or 0) > 0)
        return round(late / len(pmts), 4)

    feats.delinquency_rate_30d  = _late_rate(pmts_30)
    feats.delinquency_rate_90d  = _late_rate(pmts_90)
    feats.delinquency_rate_180d = _late_rate(pmts_180)

    # ── Total late + avg days late ───────────────────────────────────────────
    late_pmts = [p for p in all_pmts if (p.get("days_late") or 0) > 0]
    feats.total_late_payments = len(late_pmts)
    if late_pmts:
        feats.avg_days_late = round(mean(p["days_late"] for p in late_pmts), 1)

    # ── Delinquency streaks ──────────────────────────────────────────────────
    sorted_pmts = sorted(all_pmts, key=lambda p: _parse_date(p.get("due_date")) or date.min)
    max_streak = cur_streak = 0
    for p in sorted_pmts:
        if (p.get("days_late") or 0) > 0:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 0

    feats.max_delinquency_streak = max_streak
    # Current streak = trailing late payments from most recent
    trailing = 0
    for p in reversed(sorted_pmts):
        if (p.get("days_late") or 0) > 0:
            trailing += 1
        else:
            break
    feats.current_delinquency_streak = trailing

    # ── Payment regularity (CoV of amounts paid) ─────────────────────────────
    amounts = [float(p.get("amount_paid") or 0) for p in all_pmts if p.get("amount_paid")]
    if len(amounts) >= 2:
        m = mean(amounts)
        if m > 0:
            feats.payment_cv = round(stdev(amounts) / m, 4)

    # ── Early repayment rate ─────────────────────────────────────────────────
    def _is_early(p: Dict) -> bool:
        paid = _parse_date(p.get("paid_date"))
        due  = _parse_date(p.get("due_date"))
        return paid is not None and due is not None and paid < due

    feats.early_repayment_rate = round(
        sum(1 for p in all_pmts if _is_early(p)) / len(all_pmts), 4
    )

    # ── Partial payment rate (paid < 95% of due) ─────────────────────────────
    def _is_partial(p: Dict) -> bool:
        due = float(p.get("amount_due") or 0)
        paid = float(p.get("amount_paid") or 0)
        return due > 0 and paid < due * 0.95

    feats.partial_payment_rate = round(
        sum(1 for p in all_pmts if _is_partial(p)) / len(all_pmts), 4
    )

    return feats


def _parse_date(val: Any) -> Optional[date]:
    """Parse a date value that may be a date, datetime, or ISO string."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(val)).date()
    except (ValueError, TypeError):
        return None
