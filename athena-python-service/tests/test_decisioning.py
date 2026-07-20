"""
Phase 4 — risk-based pricing + affordability/DTI unit tests (pure logic in
scoring/pricing.py; endpoint wiring is live-verified against the running
service).
"""
import pytest

from scoring import pricing
from scoring.pricing import (
    assess_affordability,
    band_for_score,
    flat_monthly_installment,
    limit_for,
    max_principal_for_installment,
    rate_bands,
    risk_adjusted_rate,
)

ALL_BANDS = ["Excellent", "Very Good", "Good", "Fair", "Marginal", "Poor"]


# ── Rate band table ─────────────────────────────────────────────────────────

class TestRateBands:
    def test_all_bands_present(self):
        assert set(rate_bands()) == set(ALL_BANDS)

    def test_rates_monotonically_increase_with_risk(self):
        rates = [rate_bands()[b] for b in ALL_BANDS]
        assert rates == sorted(rates)
        assert all(0 < r < 1 for r in rates)

    def test_band_boundaries_match_pdo_bands(self):
        # Exact PDO band edges must map onto the pricing table cleanly.
        assert band_for_score(850) == "Excellent"
        assert band_for_score(780) == "Excellent"
        assert band_for_score(779) == "Very Good"
        assert band_for_score(720) == "Very Good"
        assert band_for_score(719) == "Good"
        assert band_for_score(680) == "Good"
        assert band_for_score(679) == "Fair"
        assert band_for_score(640) == "Fair"
        assert band_for_score(639) == "Marginal"
        assert band_for_score(600) == "Marginal"
        assert band_for_score(599) == "Poor"
        assert band_for_score(300) == "Poor"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("PRICING_RATE_BANDS", '{"Poor": 0.099}')
        assert rate_bands()["Poor"] == 0.099
        assert rate_bands()["Excellent"] == 0.030  # untouched defaults survive

    def test_bad_env_override_falls_back(self, monkeypatch):
        monkeypatch.setenv("PRICING_RATE_BANDS", "not-json")
        assert rate_bands() == pricing._DEFAULT_RATE_BANDS


# ── Risk-adjusted rate ──────────────────────────────────────────────────────

class TestRiskAdjustedRate:
    def test_zero_pd_gives_base_rate(self):
        r = risk_adjusted_rate(800, 0.0)
        assert r.band == "Excellent"
        assert r.risk_premium_monthly == 0.0
        assert r.monthly_rate == r.base_monthly_rate
        assert not r.capped

    def test_premium_formula(self):
        # premium = PD * LGD / 12
        r = risk_adjusted_rate(700, 0.12)
        assert r.risk_premium_monthly == pytest.approx(0.12 * r.lgd / 12, abs=1e-6)
        assert r.monthly_rate == pytest.approx(
            r.base_monthly_rate + r.risk_premium_monthly, abs=1e-6)

    def test_rate_is_capped(self):
        r = risk_adjusted_rate(310, 0.95)  # Poor base 12% + big premium
        assert r.capped
        assert r.monthly_rate == pricing.max_monthly_rate()

    def test_negative_pd_clamped(self):
        r = risk_adjusted_rate(700, -0.5)
        assert r.risk_premium_monthly == 0.0


# ── Limit ladder ────────────────────────────────────────────────────────────

class TestLimitLadder:
    def test_first_time_borrower(self):
        d = limit_for(700, closed_loans=0)
        assert d.borrower_type == "FIRST_TIME"
        assert d.multiplier == 1.0
        assert d.max_loan_amount == d.base_limit == 20_000.0  # Good band

    def test_repeat_borrower_steps(self):
        d = limit_for(700, closed_loans=2)
        assert d.borrower_type == "REPEAT"
        assert d.multiplier == 1.0 + 2 * pricing.repeat_step()
        assert d.max_loan_amount == pytest.approx(d.base_limit * d.multiplier)

    def test_ladder_caps_at_max_steps(self):
        capped = limit_for(700, closed_loans=100)
        at_cap = limit_for(700, closed_loans=pricing.repeat_max_steps())
        assert capped.max_loan_amount == at_cap.max_loan_amount

    def test_poor_band_gets_smallest_limit(self):
        assert limit_for(400, 0).base_limit < limit_for(800, 0).base_limit


# ── Installment math ────────────────────────────────────────────────────────

class TestInstallmentMath:
    def test_flat_installment(self):
        # 10,000 @ 5% flat monthly over 4 months: 2,500 principal + 500 interest
        assert flat_monthly_installment(10_000, 0.05, 4) == 3_000.0

    def test_single_month_term(self):
        assert flat_monthly_installment(10_000, 0.05, 1) == 10_500.0

    def test_zero_term_raises(self):
        with pytest.raises(ValueError):
            flat_monthly_installment(10_000, 0.05, 0)

    def test_inverse_roundtrip(self):
        inst = flat_monthly_installment(25_000, 0.07, 6)
        assert max_principal_for_installment(inst, 0.07, 6) == pytest.approx(25_000, abs=0.01)

    def test_zero_installment_zero_principal(self):
        assert max_principal_for_installment(0, 0.05, 4) == 0.0


# ── Affordability / DTI ─────────────────────────────────────────────────────

class TestAffordability:
    def test_affordable_case(self):
        # income 50k, no obligations, 10k loan @5% for 4 months → 3k/month = 6% DTI
        r = assess_affordability(50_000, 0, 10_000, 4, 0.05)
        assert r.decision == "AFFORDABLE"
        assert r.dti_with_loan == pytest.approx(0.06, abs=1e-4)
        assert r.disposable_income_after_loan == pytest.approx(47_000)
        assert r.max_affordable_installment == pytest.approx(20_000)  # 40% of income

    def test_dti_exactly_at_cap_is_affordable(self):
        # installment 3,000/mo on 10k/4mo@5%; obligations tuned so DTI == 0.40
        r = assess_affordability(10_000, 1_000, 10_000, 4, 0.05)
        assert r.dti_with_loan == pytest.approx(0.40, abs=1e-6)
        assert r.decision == "AFFORDABLE"

    def test_stretched_band(self):
        # DTI between pti_cap (0.40) and stretch_cap (0.50)
        r = assess_affordability(10_000, 1_500, 10_000, 4, 0.05)
        assert r.dti_with_loan == pytest.approx(0.45, abs=1e-6)
        assert r.decision == "STRETCHED"

    def test_dti_exactly_at_stretch_cap_is_stretched(self):
        r = assess_affordability(10_000, 2_000, 10_000, 4, 0.05)
        assert r.dti_with_loan == pytest.approx(0.50, abs=1e-6)
        assert r.decision == "STRETCHED"

    def test_unaffordable_above_stretch(self):
        r = assess_affordability(10_000, 2_100, 10_000, 4, 0.05)
        assert r.decision == "UNAFFORDABLE"

    def test_zero_income_is_unaffordable_not_crash(self):
        r = assess_affordability(0, 0, 10_000, 4, 0.05)
        assert r.decision == "UNAFFORDABLE"
        assert r.dti_current is None and r.dti_with_loan is None
        assert r.max_affordable_installment == 0.0
        assert r.max_loan_amount == 0.0

    def test_obligations_exceed_cap_floor_max_at_zero(self):
        # 40% of 10k = 4k < 5k obligations → nothing affordable
        r = assess_affordability(10_000, 5_000, 10_000, 4, 0.05)
        assert r.max_affordable_installment == 0.0
        assert r.max_loan_amount == 0.0
        assert r.decision == "UNAFFORDABLE"

    def test_max_loan_amount_consistency(self):
        # Borrowing exactly max_loan_amount must yield DTI == pti_cap
        r = assess_affordability(60_000, 4_000, 10_000, 6, 0.06)
        r2 = assess_affordability(60_000, 4_000, r.max_loan_amount, 6, 0.06)
        assert r2.dti_with_loan == pytest.approx(r.pti_cap, abs=1e-3)
        assert r2.decision == "AFFORDABLE"

    def test_negative_obligations_clamped(self):
        r = assess_affordability(50_000, -100, 10_000, 4, 0.05)
        assert r.existing_monthly_obligations == 0.0
