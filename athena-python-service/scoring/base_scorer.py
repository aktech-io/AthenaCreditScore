from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional


@dataclass
class BaseScoreResult:
    income_stability_score: float   # 0-150
    avg_monthly_income_score: float # 0-150
    savings_rate_score: float       # 0-100
    low_balance_score: float        # 0-150
    transaction_diversity_score: float  # 0-150
    base_total: float               # 300-700
    avg_monthly_income: float
    income_cv: float
    avg_monthly_savings: float
    low_balance_events: int
    category_breakdown: Dict[str, float]
    analysis_period_days: int
    patterns: str


def calculate_base_score(
    transactions: List[Dict],
    analysis_period_days: int = 180,
) -> BaseScoreResult:
    """
    Compute the quantitative base score (300-700) from transaction data.
    Implements the Athena scorecard from the white paper Section 5.2.
    """
    cutoff = date.today() - timedelta(days=analysis_period_days)
    tx_window = [
        t for t in transactions
        if isinstance(t.get("transaction_date"), date) and t["transaction_date"] >= cutoff
    ]

    # Group credits by month for income analysis
    monthly_credits: Dict[str, float] = {}
    monthly_debits: Dict[str, float] = {}
    category_totals: Dict[str, float] = {}
    low_balance_events = 0

    for t in tx_window:
        month_key = t["transaction_date"].strftime("%Y-%m")
        amount = float(t.get("amount", 0))
        tx_type = t.get("transaction_type", "").upper()
        category = t.get("category", "OTHER")

        if tx_type == "CREDIT":
            monthly_credits[month_key] = monthly_credits.get(month_key, 0) + amount
        elif tx_type == "DEBIT":
            monthly_debits[month_key] = monthly_debits.get(month_key, 0) + amount
            category_totals[category] = category_totals.get(category, 0) + amount

        # Low balance event: balance drops below 10% of avg monthly income
        if t.get("balance_after") is not None and t["balance_after"] < 0:
            low_balance_events += 1

    monthly_income_list = list(monthly_credits.values()) or [0.0]
    avg_monthly_income = statistics.mean(monthly_income_list)

    # ── 1. Income Stability (CV-based) — 0 to 150 pts ──────────────────────
    if len(monthly_income_list) > 1 and avg_monthly_income > 0:
        std_dev = statistics.stdev(monthly_income_list)
        income_cv = std_dev / avg_monthly_income
    else:
        income_cv = 1.0  # worst case if only 1 month

    if income_cv < 0.10:
        income_stability_score = 150.0
    elif income_cv < 0.20:
        income_stability_score = 120.0
    elif income_cv < 0.35:
        income_stability_score = 80.0
    elif income_cv < 0.50:
        income_stability_score = 40.0
    else:
        income_stability_score = 10.0

    # Identify low-balance events properly
    avg_income = avg_monthly_income if avg_monthly_income > 0 else 1.0
    threshold = avg_income * 0.10
    low_balance_events = sum(
        1 for t in tx_window
        if t.get("balance_after") is not None and float(t.get("balance_after", 0)) < threshold
    )

    # ── 2. Average Monthly Income — 0 to 150 pts ───────────────────────────
    if avg_monthly_income > 100_000:
        avg_monthly_income_score = 150.0
    elif avg_monthly_income > 50_000:
        avg_monthly_income_score = 120.0
    elif avg_monthly_income > 20_000:
        avg_monthly_income_score = 80.0
    elif avg_monthly_income > 5_000:
        avg_monthly_income_score = 40.0
    else:
        avg_monthly_income_score = 10.0

    # ── 3. Savings Rate — 0 to 100 pts ─────────────────────────────────────
    total_credits = sum(monthly_credits.values())
    total_debits = sum(monthly_debits.values())
    net_savings = total_credits - total_debits
    savings_rate = net_savings / total_credits if total_credits > 0 else 0
    avg_monthly_savings = net_savings / max(len(monthly_credits), 1)

    if savings_rate > 0.30:
        savings_rate_score = 100.0
    elif savings_rate > 0.15:
        savings_rate_score = 75.0
    elif savings_rate > 0.05:
        savings_rate_score = 50.0
    elif savings_rate >= 0:
        savings_rate_score = 25.0
    else:
        savings_rate_score = 0.0

    # ── 4. Low Balance Events — 0 to 150 pts ───────────────────────────────
    if low_balance_events == 0:
        low_balance_score = 150.0
    elif low_balance_events <= 1:
        low_balance_score = 100.0
    elif low_balance_events <= 3:
        low_balance_score = 50.0
    else:
        low_balance_score = 10.0

    # ── 5. Transaction Diversity — 0 to 150 pts ────────────────────────────
    unique_categories = len(category_totals)
    if unique_categories >= 6:
        transaction_diversity_score = 150.0
    elif unique_categories >= 4:
        transaction_diversity_score = 100.0
    elif unique_categories >= 2:
        transaction_diversity_score = 60.0
    else:
        transaction_diversity_score = 20.0

    # ── Total Base Score 300–700 ────────────────────────────────────────────
    raw_total = (
        income_stability_score
        + avg_monthly_income_score
        + savings_rate_score
        + low_balance_score
        + transaction_diversity_score
    )
    # Scale 10-700 → 300-700 (min floor at 300)
    base_total = max(300.0, min(700.0, 300 + (raw_total / 700) * 400))

    # Category breakdown as % of total debits
    total_debit_amount = sum(category_totals.values()) or 1.0
    category_breakdown = {
        k: round(v / total_debit_amount * 100, 1)
        for k, v in sorted(category_totals.items(), key=lambda x: -x[1])
    }

    # Identify notable patterns
    patterns_list = []
    if category_breakdown.get("SALARY", 0) > 0:
        patterns_list.append("Regular salary credits detected")
    if category_breakdown.get("BETTING", 0) and category_breakdown["BETTING"] > 3:
        patterns_list.append(f"Betting spend: {category_breakdown['BETTING']}% of debits")
    if savings_rate < 0:
        patterns_list.append("Net negative savings in period")
    patterns = "; ".join(patterns_list) if patterns_list else "No notable patterns"

    return BaseScoreResult(
        income_stability_score=income_stability_score,
        avg_monthly_income_score=avg_monthly_income_score,
        savings_rate_score=savings_rate_score,
        low_balance_score=low_balance_score,
        transaction_diversity_score=transaction_diversity_score,
        base_total=round(base_total, 2),
        avg_monthly_income=round(avg_monthly_income, 2),
        income_cv=round(income_cv, 4),
        avg_monthly_savings=round(avg_monthly_savings, 2),
        low_balance_events=low_balance_events,
        category_breakdown=category_breakdown,
        analysis_period_days=analysis_period_days,
        patterns=patterns,
    )
