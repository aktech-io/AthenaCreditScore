"""
Tests for features/pipeline.py v2 M-Pesa cash-flow feature computation.
"""
from datetime import datetime

from features.pipeline import (
    FEATURE_NAMES,
    _MPESA_DEFAULTS,
    mpesa_features_from_rows,
)


def txn(time, category, direction, amount, balance=None, counterparty=None):
    return {
        "txn_time": time, "category": category, "direction": direction,
        "amount": amount, "balance": balance, "counterparty": counterparty,
    }


class TestNoData:
    def test_defaults_flag_missing_data(self):
        f = mpesa_features_from_rows([])
        assert f == _MPESA_DEFAULTS
        assert f["has_mpesa_data"] == 0

    def test_all_mpesa_features_declared(self):
        assert set(_MPESA_DEFAULTS.keys()) <= set(FEATURE_NAMES)


class TestCashFlowFeatures:
    def make_rows(self):
        return [
            # Month 1: salary in, spend out
            txn(datetime(2026, 3, 1, 9), "SALARY", "IN", 50_000.0, balance=50_100.0),
            txn(datetime(2026, 3, 5, 12), "UTILITY", "OUT", 2_000.0, balance=48_100.0,
                counterparty="KPLC PREPAID"),
            txn(datetime(2026, 3, 10, 12), "MERCHANT", "OUT", 8_000.0, balance=40_100.0,
                counterparty="NAIVAS"),
            txn(datetime(2026, 3, 20, 12), "SAVINGS_DEPOSIT", "OUT", 10_000.0, balance=30_100.0),
            # Month 2: salary + fuliza cycle
            txn(datetime(2026, 4, 1, 9), "SALARY", "IN", 50_000.0, balance=80_100.0),
            txn(datetime(2026, 4, 3, 12), "BETTING", "OUT", 5_000.0, balance=75_100.0,
                counterparty="BETIKA"),
            txn(datetime(2026, 4, 25, 12), "FULIZA_DRAW", "IN", 1_000.0, balance=50.0),
            txn(datetime(2026, 4, 28, 12), "FULIZA_REPAY", "OUT", 1_050.0, balance=20.0),
            # Month 3: only a small transfer in
            txn(datetime(2026, 5, 15, 12), "RECEIVED", "IN", 3_000.0, balance=3_020.0),
        ]

    def test_month_span_and_regularity(self):
        f = mpesa_features_from_rows(self.make_rows())
        assert f["has_mpesa_data"] == 1
        assert f["mpesa_months_observed"] == 3
        assert f["mpesa_income_regularity"] == 1.0  # inflow in every observed month

    def test_fuliza_draw_not_income(self):
        f = mpesa_features_from_rows(self.make_rows())
        # inflow months: 50k, 50k, 3k — Fuliza draw excluded
        assert f["mpesa_monthly_inflow_avg"] == round((50_000 + 50_000 + 3_000) / 3, 2)
        assert f["mpesa_fuliza_draw_count"] == 1

    def test_spend_ratios(self):
        f = mpesa_features_from_rows(self.make_rows())
        total_out = 2_000 + 8_000 + 10_000 + 5_000 + 1_050
        assert f["mpesa_betting_ratio"] == round(5_000 / total_out, 4)
        assert f["mpesa_savings_ratio"] == round(10_000 / total_out, 4)
        assert f["mpesa_loan_repay_ratio"] == round(1_050 / total_out, 4)

    def test_low_balance_rate(self):
        f = mpesa_features_from_rows(self.make_rows())
        # balances < 100 KES: 50.0 and 20.0 out of 9 known balances
        assert f["mpesa_low_balance_rate"] == round(2 / 9, 4)

    def test_merchant_diversity_counts_billers(self):
        f = mpesa_features_from_rows(self.make_rows())
        assert f["mpesa_merchant_diversity"] == 2  # KPLC + NAIVAS (betting not a merchant)

    def test_single_month_no_cv(self):
        rows = [txn(datetime(2026, 5, 1, 9), "SALARY", "IN", 10_000.0)]
        f = mpesa_features_from_rows(rows)
        assert f["mpesa_inflow_cv"] == 0.0
        assert f["mpesa_outflow_inflow_ratio"] == 0.0
