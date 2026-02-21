from __future__ import annotations

from datetime import date, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ApplicationFeatures:
    """Application-time features derived from business/applicant profile."""
    capital_growth_ratio: float
    revenue_per_employee: float
    profit_margin: float
    profit_per_employee: float
    sector_density: int
    region_density: int


@dataclass
class PerformanceFeatures:
    """Repeat-borrower behavioural features derived from loan history."""
    num_past_loans: int
    avg_principal: float
    total_penalties: float
    penalty_rate: float
    max_consecutive_ontime: int
    max_consecutive_late: int
    rolling_avg_payment_3m: float
    rolling_avg_payment_6m: float
    rolling_avg_payment_12m: float
    avg_days_between_loans: float


def compute_application_features(
    current_capital: float,
    initial_capital: float,
    annual_revenue: float,
    net_profit: float,
    num_employees: int,
    sector: str,
    region: str,
    sector_counts: Dict[str, int],
    region_counts: Dict[str, int],
) -> ApplicationFeatures:
    """
    Compute ratio-based application features as described in Scoring.pdf Section 5.1.
    """
    safe_div = lambda a, b: a / b if b and b != 0 else 0.0

    capital_growth_ratio = safe_div(current_capital - initial_capital, initial_capital)
    revenue_per_employee = safe_div(annual_revenue, num_employees)
    profit_margin = safe_div(net_profit, annual_revenue)
    profit_per_employee = safe_div(net_profit, num_employees)
    sector_density = sector_counts.get(sector, 0)
    region_density = region_counts.get(region, 0)

    return ApplicationFeatures(
        capital_growth_ratio=round(capital_growth_ratio, 4),
        revenue_per_employee=round(revenue_per_employee, 2),
        profit_margin=round(profit_margin, 4),
        profit_per_employee=round(profit_per_employee, 2),
        sector_density=sector_density,
        region_density=region_density,
    )


def compute_performance_features(
    repayments: List[Dict[str, Any]],
    loans: List[Dict[str, Any]],
) -> PerformanceFeatures:
    """
    Compute behavioural performance features for repeat borrowers.
    Implements Scoring.pdf Section 5.2 indicators.
    """
    if not loans:
        return PerformanceFeatures(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    num_past_loans = len(loans)
    principals = [float(ln.get("principal_amount", 0)) for ln in loans]
    avg_principal = sum(principals) / num_past_loans

    # Penalties
    total_penalties = sum(float(r.get("penalty_amount", 0)) for r in repayments)
    total_paid = sum(float(r.get("amount_paid", 0)) for r in repayments)
    penalty_rate = total_penalties / total_paid if total_paid > 0 else 0.0

    # Delinquency streaks
    sorted_repayments = sorted(repayments, key=lambda r: r.get("payment_date", date.min))
    max_consecutive_ontime = 0
    max_consecutive_late = 0
    cur_ontime = 0
    cur_late = 0
    for rep in sorted_repayments:
        days_late = int(rep.get("days_late", 0))
        if days_late == 0:
            cur_ontime += 1
            cur_late = 0
        else:
            cur_late += 1
            cur_ontime = 0
        max_consecutive_ontime = max(max_consecutive_ontime, cur_ontime)
        max_consecutive_late = max(max_consecutive_late, cur_late)

    # Rolling average payment amounts
    today = date.today()
    def avg_payment_in_window(months: int) -> float:
        cutoff = today - timedelta(days=months * 30)
        window = [
            float(r.get("amount_paid", 0))
            for r in sorted_repayments
            if isinstance(r.get("payment_date"), date) and r["payment_date"] >= cutoff
        ]
        return sum(window) / len(window) if window else 0.0

    rolling_3m = avg_payment_in_window(3)
    rolling_6m = avg_payment_in_window(6)
    rolling_12m = avg_payment_in_window(12)

    # Loan spacing (days between disbursements)
    disbursement_dates = sorted(
        [ln.get("disbursement_date") for ln in loans if ln.get("disbursement_date")],
    )
    if len(disbursement_dates) >= 2:
        gaps = [
            (disbursement_dates[i + 1] - disbursement_dates[i]).days
            for i in range(len(disbursement_dates) - 1)
        ]
        avg_days_between = sum(gaps) / len(gaps)
    else:
        avg_days_between = 0.0

    return PerformanceFeatures(
        num_past_loans=num_past_loans,
        avg_principal=round(avg_principal, 2),
        total_penalties=round(total_penalties, 2),
        penalty_rate=round(penalty_rate, 6),
        max_consecutive_ontime=max_consecutive_ontime,
        max_consecutive_late=max_consecutive_late,
        rolling_avg_payment_3m=round(rolling_3m, 2),
        rolling_avg_payment_6m=round(rolling_6m, 2),
        rolling_avg_payment_12m=round(rolling_12m, 2),
        avg_days_between_loans=round(avg_days_between, 1),
    )
