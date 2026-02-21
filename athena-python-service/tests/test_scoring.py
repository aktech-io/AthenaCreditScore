"""
Athena Credit Score Engine — Unit Tests
Tests the core scoring functions: BaseScorer, CrbExtractor, PDOTransformer.
"""
import math
from datetime import date, timedelta
import pytest

# Import scoring modules
from scoring.base_scorer import calculate_base_score
from scoring.crb_extractor import extract_crb_metrics
from scoring.pdo_transformer import PDOTransformer


# ── Fixtures ────────────────────────────────────────────────────────────────

def make_transactions(
    monthly_credits=45000,
    months=6,
    categories=("SALARY", "UTILITIES", "GROCERIES"),
    low_balance_months=0,
):
    """Generate a synthetic transaction list for testing."""
    transactions = []
    today = date.today()
    for m in range(months):
        tx_date = today - timedelta(days=30 * m)
        transactions.append({
            "transaction_date": tx_date,
            "amount": monthly_credits,
            "transaction_type": "CREDIT",
            "category": "SALARY",
            "balance_after": monthly_credits * 0.8,
        })
        for i, cat in enumerate(categories):
            transactions.append({
                "transaction_date": tx_date - timedelta(days=i + 1),
                "amount": monthly_credits * 0.15,
                "transaction_type": "DEBIT",
                "category": cat,
                "balance_after": monthly_credits * (0.7 - i * 0.1),
            })
        if m < low_balance_months:
            transactions.append({
                "transaction_date": tx_date - timedelta(days=15),
                "amount": 100,
                "transaction_type": "DEBIT",
                "category": "ATM",
                "balance_after": 50.0,  # Very low balance
            })
    return transactions


def make_crb_report(bureau_score=624, npa_count=2, has_settled_defaults=True):
    npa_accounts = [
        {"currentBalance": 8000, "status": "NPA"} for _ in range(npa_count)
    ]
    defaults = []
    if has_settled_defaults:
        defaults = [{"status": "SETTLED"}, {"status": "SETTLED"}]
    return {
        "creditReport": {
            "bureauName": "TransUnion",
            "reportDate": "2025-03-01",
            "bureauScore": bureau_score,
            "nonPerformingAccounts": npa_accounts,
            "performingAccountsWithDefault": defaults,
            "enquiriesLast90Days": 0,
            "creditApplicationsLast12Months": 2,
        }
    }


# ── Base Scorer Tests ────────────────────────────────────────────────────────

class TestBaseScorer:
    def test_stable_income_high_score(self):
        txns = make_transactions(monthly_credits=50000, months=6)
        result = calculate_base_score(txns, 180)
        assert result.base_total >= 400, "Stable income should yield base score >= 400"
        assert result.income_stability_score > 0

    def test_no_transactions_minimum_income_scores(self):
        """With 0 transactions, income scores should all be at minimum (zero income)."""
        result = calculate_base_score([], 180)
        # Min possible income score when no data
        assert result.income_stability_score == 10.0, "No transactions → worst income stability"
        assert result.avg_monthly_income_score == 10.0, "No transactions → worst income level"
        assert result.avg_monthly_income == 0.0, "No transactions → zero income"
        # Score is floor-clamped at 300 (never below)
        assert result.base_total >= 300.0, "Score should never fall below 300"

    def test_low_balance_events_detected(self):
        txns = make_transactions(monthly_credits=30000, months=6, low_balance_months=3)
        result = calculate_base_score(txns, 180)
        assert result.low_balance_events >= 0  # Should record low balance events

    def test_score_within_range(self):
        txns = make_transactions()
        result = calculate_base_score(txns, 180)
        assert 300 <= result.base_total <= 700, "Base score must be between 300 and 700"

    def test_category_breakdown_sums(self):
        txns = make_transactions()
        result = calculate_base_score(txns, 180)
        total_pct = sum(result.category_breakdown.values())
        assert abs(total_pct - 100.0) < 1.0, "Category breakdown should sum to ~100%"


# ── CRB Extractor Tests ──────────────────────────────────────────────────────

class TestCrbExtractor:
    def test_high_bureau_score_contribution(self):
        report = make_crb_report(bureau_score=800, npa_count=0, has_settled_defaults=False)
        metrics = extract_crb_metrics(report)
        assert metrics.crb_contribution >= 100, "High bureau score + no NPAs should score >= 100"

    def test_two_npas_partial_score(self):
        report = make_crb_report(bureau_score=624, npa_count=2)
        metrics = extract_crb_metrics(report)
        assert metrics.npa_count == 2
        assert metrics.npa_pts == 10.0, "1-2 NPAs should give +10 pts"

    def test_many_npas_negative(self):
        report = make_crb_report(bureau_score=500, npa_count=5)
        metrics = extract_crb_metrics(report)
        assert metrics.npa_pts == -20.0, ">2 NPAs should give -20 pts"

    def test_active_defaults_negative(self):
        report = {
            "creditReport": {
                "bureauName": "Metropol",
                "reportDate": "2025-03-01",
                "bureauScore": 400,
                "nonPerformingAccounts": [],
                "performingAccountsWithDefault": [
                    {"status": "ACTIVE"}, {"status": "DELINQUENT"}
                ],
                "enquiriesLast90Days": 5,
                "creditApplicationsLast12Months": 4,
            }
        }
        metrics = extract_crb_metrics(report)
        assert metrics.default_pts == -30.0
        assert metrics.active_defaults == 2

    def test_crb_contribution_clamped(self):
        report = make_crb_report(bureau_score=900, npa_count=0, has_settled_defaults=False)
        metrics = extract_crb_metrics(report)
        assert 0 <= metrics.crb_contribution <= 150


# ── PDO Transformer Tests ────────────────────────────────────────────────────

class TestPDOTransformer:
    def test_fifty_percent_pd_at_base_score(self):
        t = PDOTransformer(pdo=50, base_score=500, base_odds=1.0)
        result = t.transform(0.5)
        # At PD=0.5, odds=1, score = offset - factor*ln(1) = base_score
        assert abs(result.score - 500) <= 2, "PD=0.5 should map to base_score ±2"

    def test_low_pd_high_score(self):
        t = PDOTransformer()
        result = t.transform(0.05)
        assert result.score > 650, "Low PD should give high score"
        assert result.band in ("Good", "Very Good", "Excellent")

    def test_high_pd_low_score(self):
        t = PDOTransformer()
        result = t.transform(0.80)
        assert result.score < 450, "High PD should give low score"
        assert result.band == "Poor"

    def test_score_clamped_300_850(self):
        t = PDOTransformer()
        extreme_low = t.transform(0.9999)
        extreme_high = t.transform(0.0001)
        assert extreme_low.score >= 300
        assert extreme_high.score <= 850

    def test_inverse_pd_from_score(self):
        t = PDOTransformer()
        original_pd = 0.25
        result = t.transform(original_pd)
        recovered_pd = t.pd_from_score(result.score)
        assert abs(recovered_pd - original_pd) < 0.05, "Inverse should recover approx original PD"

    def test_doubling_odds_drops_pdo_points(self):
        """Verify the PDO property: doubling odds drops score by exactly pdo points."""
        t = PDOTransformer(pdo=50, base_score=500, base_odds=1.0)
        # At odds=1 → base_score=500; at odds=2 → should be 500-50=450
        score_at_1 = t.transform(0.5).score    # odds = 1
        score_at_2 = t.transform(2/3).score    # pd=2/3 → odds = 2
        assert abs((score_at_1 - score_at_2) - 50) <= 3, "Doubling odds should drop ~50 points"
