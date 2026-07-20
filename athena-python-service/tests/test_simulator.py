"""
Phase 4 — score simulator delta-engine unit tests (scoring/simulator.py).
Covers delta mapping on the feature vector, the transaction-level fallback,
and the read-only (no input mutation) guarantee.
"""
import copy
from datetime import date, timedelta

import pytest

from scoring.simulator import (
    FALLBACK_NO_EFFECT,
    SUPPORTED_DELTAS,
    apply_deltas,
    apply_deltas_to_transactions,
    normalize_deltas,
)


def make_features(**overrides):
    f = {
        "avg_loan_spacing_days": 45.0,
        "max_delinquency_streak": 3,
        "delinquency_rate_90d": 0.5,
        "total_loans": 4,
        "payment_cv": 0.3,
        "early_repayment_rate": 0.5,
        "capital_growth_rate": 0.0,
        "profit_margin": 0.0,
        "sector_risk_modifier": 1.0,
        "bureau_score": 600,
        "open_npa_accounts": 2,
        "has_mpesa_data": 1,
        "mpesa_months_observed": 6,
        "mpesa_monthly_inflow_avg": 40_000.0,
        "mpesa_inflow_cv": 0.2,
        "mpesa_income_regularity": 1.0,
        "mpesa_outflow_inflow_ratio": 0.9,
        "mpesa_low_balance_rate": 0.1,
        "mpesa_merchant_diversity": 5,
        "mpesa_airtime_ratio": 0.05,
        "mpesa_betting_ratio": 0.15,
        "mpesa_savings_ratio": 0.05,
        "mpesa_loan_repay_ratio": 0.1,
        "mpesa_fuliza_draw_count": 4,
    }
    f.update(overrides)
    return f


class TestNormalizeDeltas:
    def test_unknown_deltas_reported(self):
        applicable, unknown = normalize_deltas({"clear_delinquencies": True, "win_lottery": 1})
        assert "clear_delinquencies" in applicable
        assert unknown == ["win_lottery"]

    def test_falsy_boolean_switch_dropped(self):
        applicable, unknown = normalize_deltas({"clear_delinquencies": False})
        assert applicable == {} and unknown == []

    def test_zero_numeric_delta_dropped(self):
        applicable, _ = normalize_deltas({"add_monthly_savings": 0})
        assert applicable == {}

    def test_non_numeric_value_reported_unknown(self):
        _, unknown = normalize_deltas({"add_monthly_savings": "lots"})
        assert unknown == ["add_monthly_savings"]

    def test_all_supported_deltas_normalize(self):
        req = {n: (True if n in ("clear_delinquencies", "reduce_betting_to_zero",
                                 "clear_fuliza") else 5)
               for n in SUPPORTED_DELTAS}
        applicable, unknown = normalize_deltas(req)
        assert set(applicable) == set(SUPPORTED_DELTAS) and unknown == []


class TestFeatureDeltas:
    def test_clear_delinquencies(self):
        sim = apply_deltas(make_features(), {"clear_delinquencies": True})
        assert sim["max_delinquency_streak"] == 0
        assert sim["delinquency_rate_90d"] == 0.0
        assert sim["open_npa_accounts"] == 0

    def test_reduce_betting_to_zero(self):
        sim = apply_deltas(make_features(), {"reduce_betting_to_zero": True})
        assert sim["mpesa_betting_ratio"] == 0.0

    def test_add_monthly_savings_raises_ratio_bounded(self):
        f = make_features()
        sim = apply_deltas(f, {"add_monthly_savings": 5_000})
        assert sim["mpesa_savings_ratio"] > f["mpesa_savings_ratio"]
        huge = apply_deltas(f, {"add_monthly_savings": 10_000_000})
        assert huge["mpesa_savings_ratio"] == 1.0

    def test_close_loans_on_time(self):
        sim = apply_deltas(make_features(), {"close_loans_on_time": 2})
        assert sim["total_loans"] == 6
        # 2 new on-time closures must pull the early-repayment rate upward
        assert sim["early_repayment_rate"] > 0.5

    def test_increase_monthly_income_adjusts_outflow_ratio(self):
        f = make_features()
        sim = apply_deltas(f, {"increase_monthly_income": 10_000})
        assert sim["mpesa_monthly_inflow_avg"] == 50_000.0
        # outflow constant: 36k/50k = 0.72
        assert sim["mpesa_outflow_inflow_ratio"] == pytest.approx(0.72, abs=1e-3)

    def test_improve_bureau_score_capped_at_850(self):
        sim = apply_deltas(make_features(), {"improve_bureau_score": 500})
        assert sim["bureau_score"] == 850

    def test_clear_fuliza(self):
        sim = apply_deltas(make_features(), {"clear_fuliza": True})
        assert sim["mpesa_fuliza_draw_count"] == 0

    def test_combined_deltas(self):
        sim = apply_deltas(make_features(), {
            "clear_delinquencies": True,
            "reduce_betting_to_zero": True,
            "add_monthly_savings": 5_000,
        })
        assert sim["max_delinquency_streak"] == 0
        assert sim["mpesa_betting_ratio"] == 0.0
        assert sim["mpesa_savings_ratio"] > 0.05

    def test_input_features_never_mutated(self):
        f = make_features()
        snapshot = copy.deepcopy(f)
        apply_deltas(f, {n: (True if n in ("clear_delinquencies",
                                           "reduce_betting_to_zero", "clear_fuliza")
                             else 3) for n in SUPPORTED_DELTAS})
        assert f == snapshot  # read-only guarantee


class TestTransactionFallback:
    def make_txns(self):
        today = date.today()
        txns = []
        for m in range(4):
            d = today - timedelta(days=30 * m)
            txns.append({"transaction_date": d, "amount": 30_000,
                         "transaction_type": "CREDIT", "category": "SALARY",
                         "balance_after": 25_000})
            txns.append({"transaction_date": d - timedelta(days=2), "amount": 4_000,
                         "transaction_type": "DEBIT", "category": "BETTING",
                         "balance_after": 21_000})
            txns.append({"transaction_date": d - timedelta(days=3), "amount": 8_000,
                         "transaction_type": "DEBIT", "category": "GROCERIES",
                         "balance_after": 13_000})
        return txns

    def test_reduce_betting_removes_betting_debits(self):
        txns = self.make_txns()
        out, no_effect = apply_deltas_to_transactions(txns, {"reduce_betting_to_zero": True})
        assert not any(t["category"] == "BETTING" for t in out)
        assert no_effect == []

    def test_add_savings_scales_discretionary_debits(self):
        txns = self.make_txns()
        out, _ = apply_deltas_to_transactions(txns, {"add_monthly_savings": 2_000})
        betting = [t for t in out if t["category"] == "BETTING"]
        assert all(t["amount"] < 4_000 for t in betting)      # scaled down
        groceries = [t for t in out if t["category"] == "GROCERIES"]
        assert all(t["amount"] == 8_000 for t in groceries)   # essentials untouched

    def test_increase_income_adds_monthly_credit(self):
        txns = self.make_txns()
        out, _ = apply_deltas_to_transactions(txns, {"increase_monthly_income": 10_000})
        added = [t for t in out if t["transaction_type"] == "CREDIT" and t["amount"] == 10_000]
        assert len(added) == 4  # one per observed month

    def test_scorecard_inexpressible_deltas_reported(self):
        txns = self.make_txns()
        _, no_effect = apply_deltas_to_transactions(
            txns, {"clear_delinquencies": True, "improve_bureau_score": 50})
        assert set(no_effect) == {"clear_delinquencies", "improve_bureau_score"}
        assert set(no_effect) <= FALLBACK_NO_EFFECT

    def test_input_transactions_never_mutated(self):
        txns = self.make_txns()
        snapshot = copy.deepcopy(txns)
        apply_deltas_to_transactions(txns, {
            "reduce_betting_to_zero": True,
            "add_monthly_savings": 2_000,
            "increase_monthly_income": 5_000,
        })
        assert txns == snapshot  # read-only guarantee
