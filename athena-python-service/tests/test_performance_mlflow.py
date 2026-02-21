"""
Tests for performance_features.py and mlflow_client comparison logic.
"""
import pytest
from datetime import date, timedelta
from features.performance_features import compute_performance_features, PerformanceFeatures


def _loan(loan_id, days_ago_disbursed, days_ago_closed=None, status="CLOSED"):
    today = date.today()
    disbursed = today - timedelta(days=days_ago_disbursed)
    closed = (today - timedelta(days=days_ago_closed)) if days_ago_closed else None
    due = disbursed + timedelta(days=30)
    return {
        "loan_id": loan_id,
        "disbursed_date": disbursed,
        "due_date": due,
        "closed_date": closed,
        "status": status,
    }


def _pmt(loan_id, due_days_ago, days_late=0, amount_due=5000, paid_ratio=1.0):
    today = date.today()
    due_dt = today - timedelta(days=due_days_ago)
    paid_dt = due_dt + timedelta(days=days_late)
    return {
        "loan_id": loan_id,
        "due_date": due_dt,
        "paid_date": paid_dt,
        "amount_due": amount_due,
        "amount_paid": amount_due * paid_ratio,
        "days_late": days_late,
    }


# ── No-data baseline ─────────────────────────────────────────────────────────

class TestNoData:
    def test_empty_returns_zero_feats(self):
        f = compute_performance_features([], [])
        assert f.max_delinquency_streak == 0
        assert f.total_loans == 0
        assert f.delinquency_rate_90d == 0.0

    def test_loans_only_no_payments(self):
        loans = [_loan(1, 60), _loan(2, 120)]
        f = compute_performance_features(loans, [])
        assert f.total_loans == 2
        assert f.avg_loan_spacing_days == 60.0


# ── Delinquency streaks ──────────────────────────────────────────────────────

class TestDelinquencyStreaks:
    def test_consecutive_late_payments_counted(self):
        payments = [
            _pmt(1, 90),      # on time
            _pmt(1, 60, days_late=7),
            _pmt(1, 30, days_late=14),
            _pmt(1, 0,  days_late=3),
        ]
        f = compute_performance_features([_loan(1, 120)], payments)
        assert f.max_delinquency_streak == 3
        assert f.current_delinquency_streak == 3

    def test_streak_resets_on_on_time_payment(self):
        payments = [
            _pmt(1, 120, days_late=10),
            _pmt(1, 90,  days_late=5),
            _pmt(1, 60),               # on time — resets streak
            _pmt(1, 30,  days_late=2),
        ]
        f = compute_performance_features([_loan(1, 150)], payments)
        assert f.max_delinquency_streak == 2   # the first 2
        assert f.current_delinquency_streak == 1  # only last payment

    def test_all_on_time_streaks_are_zero(self):
        payments = [_pmt(1, 90), _pmt(1, 60), _pmt(1, 30)]
        f = compute_performance_features([_loan(1, 100)], payments)
        assert f.max_delinquency_streak == 0
        assert f.current_delinquency_streak == 0
        assert f.total_late_payments == 0


# ── Rolling delinquency rates ─────────────────────────────────────────────────

class TestRollingRates:
    def test_delinquency_rate_30d_only_recent(self):
        payments = [
            _pmt(1, 20, days_late=5),   # in 30d window, late
            _pmt(1, 10),                 # in 30d window, on time
            _pmt(1, 95, days_late=10),  # outside 90d window — excluded from both rates
        ]
        f = compute_performance_features([_loan(1, 120)], payments)
        # 30d window: 1 late out of 2 → 50%
        assert f.delinquency_rate_30d == pytest.approx(0.50)
        # 90d window: same 2 payments (95-day one excluded) → 50%
        assert f.delinquency_rate_90d == pytest.approx(0.50)

    def test_all_late_in_window_rate_is_one(self):
        payments = [_pmt(1, 10, days_late=5), _pmt(1, 5, days_late=3)]
        f = compute_performance_features([_loan(1, 30)], payments)
        assert f.delinquency_rate_30d == 1.0


# ── Loan spacing ─────────────────────────────────────────────────────────────

class TestLoanSpacing:
    def test_two_loans_correct_spacing(self):
        loans = [_loan(1, 180), _loan(2, 60)]
        f = compute_performance_features(loans, [])
        assert f.avg_loan_spacing_days == pytest.approx(120.0)
        assert f.min_loan_spacing_days == 120

    def test_rapid_reborrowing_detected(self):
        loans = [_loan(1, 100), _loan(2, 95), _loan(3, 60)]
        f = compute_performance_features(loans, [])
        assert f.min_loan_spacing_days == 5  # very short gap

    def test_single_loan_no_spacing(self):
        loans = [_loan(1, 90)]
        f = compute_performance_features(loans, [])
        assert f.avg_loan_spacing_days == 0.0


# ── Payment regularity & early repayment ─────────────────────────────────────

class TestPaymentBehaviour:
    def test_regular_same_amount_cv_near_zero(self):
        payments = [_pmt(1, d, amount_due=5000, paid_ratio=1.0) for d in [90, 60, 30]]
        f = compute_performance_features([_loan(1, 100)], payments)
        assert f.payment_cv == pytest.approx(0.0, abs=0.001)

    def test_early_repayment_rate(self):
        today = date.today()
        payments = [
            {  # Paid 5 days BEFORE due
                "loan_id": 1,
                "due_date": today - timedelta(days=30),
                "paid_date": today - timedelta(days=35),
                "amount_due": 5000,
                "amount_paid": 5000,
                "days_late": 0,
            },
            _pmt(1, 10),  # Paid on due date (not early)
        ]
        f = compute_performance_features([_loan(1, 60)], payments)
        assert f.early_repayment_rate == pytest.approx(0.5)

    def test_partial_payment_rate(self):
        payments = [
            _pmt(1, 60, paid_ratio=0.5),   # partial (< 95%)
            _pmt(1, 30, paid_ratio=1.0),   # full
            _pmt(1, 10, paid_ratio=0.94),  # partial
        ]
        f = compute_performance_features([_loan(1, 80)], payments)
        assert f.partial_payment_rate == pytest.approx(2 / 3, abs=0.01)


# ── mlflow_client compare logic (pure, no network) ───────────────────────────

class TestMlflowClientCompare:
    """
    Test the recommendation logic of compare_champion_challenger using
    the decision thresholds directly (without hitting MLflow server).
    """

    def _recommendation(self, champ_ks, chall_ks, champ_auc, chall_auc):
        """Mirror the recommendation logic from mlflow_client.py."""
        ks_improvement  = chall_ks  - champ_ks
        auc_improvement = chall_auc - champ_auc
        if ks_improvement >= 0.02 or auc_improvement >= 0.005:
            return "promote_challenger"
        elif ks_improvement <= -0.03 or auc_improvement <= -0.01:
            return "rollback_challenger"
        return "keep_champion"

    def test_promote_on_ks_improvement(self):
        assert self._recommendation(0.30, 0.33, 0.80, 0.80) == "promote_challenger"

    def test_promote_on_auc_improvement(self):
        assert self._recommendation(0.30, 0.30, 0.80, 0.806) == "promote_challenger"

    def test_rollback_on_ks_drop(self):
        assert self._recommendation(0.35, 0.31, 0.84, 0.83) == "rollback_challenger"

    def test_rollback_on_auc_drop(self):
        assert self._recommendation(0.35, 0.35, 0.84, 0.825) == "rollback_challenger"

    def test_keep_when_marginal_difference(self):
        assert self._recommendation(0.30, 0.31, 0.80, 0.803) == "keep_champion"
