"""
Tests for features/pipeline.py v3 SME bank-statement cash-flow feature computation.
"""
from datetime import datetime

from features.pipeline import (
    FEATURE_NAMES,
    LGBM_FEATURE_VERSION,
    _BANK_DEFAULTS,
    bank_features_from_rows,
)


def txn(time, category, direction, amount, balance=None):
    return {
        "txn_time": time, "category": category, "direction": direction,
        "amount": amount, "balance": balance,
    }


class TestNoData:
    def test_defaults_flag_missing_data(self):
        f = bank_features_from_rows([])
        assert f == _BANK_DEFAULTS
        assert f["has_bank_data"] == 0
        assert f["bank_tax_paid_flag"] == 0

    def test_all_bank_features_declared(self):
        assert set(_BANK_DEFAULTS.keys()) <= set(FEATURE_NAMES)

    def test_feature_version_bumped_to_v3(self):
        assert LGBM_FEATURE_VERSION == "3"


class TestSmeCashFlowFeatures:
    def make_rows(self):
        """Six months of a small hardware SME: steady sales, payroll, one tax
        remittance, a loan cycle."""
        rows = []
        for month in range(1, 7):  # Jan..Jun 2026
            rows.append(txn(datetime(2026, month, 1, 9), "SALES_INCOME", "IN", 100_000.0))
            rows.append(txn(datetime(2026, month, 5, 12), "PAYROLL", "OUT", 30_000.0))
        rows.append(txn(datetime(2026, 2, 9, 10), "TAX", "OUT", 5_000.0))
        rows.append(txn(datetime(2026, 3, 12, 10), "SUPPLIER_PAYMENT", "OUT", 40_000.0))
        rows.append(txn(datetime(2026, 4, 15, 10), "BANK_CHARGES", "OUT", 1_000.0))
        rows.append(txn(datetime(2026, 5, 2, 10), "LOAN_DISBURSEMENT", "IN", 50_000.0))
        rows.append(txn(datetime(2026, 6, 25, 10), "LOAN_REPAYMENT", "OUT", 10_000.0))
        return sorted(rows, key=lambda r: r["txn_time"])

    def test_month_span_and_inflow(self):
        f = bank_features_from_rows(self.make_rows())
        assert f["has_bank_data"] == 1
        assert f["bank_months_observed"] == 6
        # Loan disbursement is liquidity, not revenue — excluded from inflow.
        assert f["bank_monthly_inflow_avg"] == 100_000.0
        assert f["bank_inflow_cv"] == 0.0  # perfectly steady sales

    def test_outflow_ratios(self):
        f = bank_features_from_rows(self.make_rows())
        total_out = 6 * 30_000 + 5_000 + 40_000 + 1_000 + 10_000  # 236,000
        assert f["bank_payroll_ratio"] == round(6 * 30_000 / total_out, 4)
        assert f["bank_supplier_ratio"] == round(40_000 / total_out, 4)
        assert f["bank_charges_ratio"] == round(1_000 / total_out, 4)
        assert f["bank_loan_repay_ratio"] == round(10_000 / total_out, 4)
        # total inflow includes the disbursement (it is real liquidity in).
        assert f["bank_outflow_inflow_ratio"] == round(total_out / (6 * 100_000 + 50_000), 4)

    def test_tax_paid_flag(self):
        f = bank_features_from_rows(self.make_rows())
        assert f["bank_tax_paid_flag"] == 1
        no_tax = [t for t in self.make_rows() if t["category"] != "TAX"]
        assert bank_features_from_rows(no_tax)["bank_tax_paid_flag"] == 0

    def test_single_month_no_cv_no_outflow(self):
        rows = [txn(datetime(2026, 5, 1, 9), "SALES_INCOME", "IN", 10_000.0)]
        f = bank_features_from_rows(rows)
        assert f["bank_months_observed"] == 1
        assert f["bank_inflow_cv"] == 0.0
        assert f["bank_outflow_inflow_ratio"] == 0.0
        assert f["bank_payroll_ratio"] == 0.0
