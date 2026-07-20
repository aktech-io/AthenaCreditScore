"""
Phase 4 — collections-priority score unit tests (pure logic in
scoring/collections_priority.py; endpoint wiring is live-verified against the
running service, mirroring the pricing/affordability test split).
"""
import pytest

from scoring.collections_priority import (
    ABILITY_STRONG,
    ABILITY_UNKNOWN,
    ABILITY_WEAK,
    PRIORITY_BANDS,
    ability_component,
    ability_to_pay,
    band_cutoffs,
    behaviour_component,
    collections_priority,
    exposure_component,
    recommended_action,
    risk_component,
    urgency_component,
)

MPESA_STRONG = {"has_mpesa_data": 1, "mpesa_monthly_inflow_avg": 80_000, "mpesa_low_balance_rate": 0.1}
MPESA_WEAK = {"has_mpesa_data": 1, "mpesa_monthly_inflow_avg": 0, "mpesa_low_balance_rate": 0.9}


# ── Components ──────────────────────────────────────────────────────────────

class TestRiskComponent:
    def test_linear_in_pd(self):
        assert risk_component(0.0) == 0.0
        assert risk_component(0.5) == 15.0
        assert risk_component(1.0) == 30.0

    def test_pd_clamped(self):
        assert risk_component(-0.2) == 0.0
        assert risk_component(1.7) == 30.0


class TestExposureComponent:
    def test_zero_outstanding_is_zero(self):
        assert exposure_component(0) == 0.0

    def test_reference_amount_earns_half_weight(self):
        assert exposure_component(50_000) == 15.0  # default ref

    def test_saturates_below_max(self):
        big = exposure_component(10_000_000)
        assert 29.0 < big < 30.0

    def test_monotonic(self):
        vals = [exposure_component(a) for a in (1_000, 10_000, 100_000, 1_000_000)]
        assert vals == sorted(vals)

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("COLLECTIONS_EXPOSURE_REF", "10000")
        assert exposure_component(10_000) == 15.0


class TestUrgencyCurve:
    def test_not_delinquent_is_zero(self):
        assert urgency_component(0) == 0.0

    def test_peaks_in_roll_rate_window(self):
        peak = urgency_component(75)
        for d in (3, 20, 45, 120, 400):
            assert urgency_component(d) < peak

    def test_self_cure_window_below_mid_stage(self):
        assert urgency_component(5) < urgency_component(45)

    def test_declines_past_write_off_zone(self):
        assert urgency_component(200) < urgency_component(120) < urgency_component(90)


class TestBehaviourComponent:
    def test_neutral_base(self):
        assert behaviour_component(0, 0) == 5.0

    def test_broken_promises_raise(self):
        assert behaviour_component(1, 0) == 7.5
        assert behaviour_component(2, 0) == 10.0
        assert behaviour_component(5, 0) == 10.0  # capped

    def test_kept_promises_lower(self):
        assert behaviour_component(0, 2) == 0.0
        assert behaviour_component(0, 9) == 0.0  # capped, floored

    def test_mixed_cancels(self):
        assert behaviour_component(1, 1) == 5.0


class TestAbilityToPay:
    def test_no_features_unknown(self):
        assert ability_to_pay(None) == ABILITY_UNKNOWN
        assert ability_to_pay({"has_mpesa_data": 0}) == ABILITY_UNKNOWN

    def test_strong(self):
        assert ability_to_pay(MPESA_STRONG) == ABILITY_STRONG

    def test_weak_on_no_inflow_or_chronic_low_balance(self):
        assert ability_to_pay(MPESA_WEAK) == ABILITY_WEAK
        assert ability_to_pay({"has_mpesa_data": 1, "mpesa_monthly_inflow_avg": 50_000,
                               "mpesa_low_balance_rate": 0.8}) == ABILITY_WEAK

    def test_middle_ground_unknown(self):
        assert ability_to_pay({"has_mpesa_data": 1, "mpesa_monthly_inflow_avg": 50_000,
                               "mpesa_low_balance_rate": 0.5}) == ABILITY_UNKNOWN

    def test_component_ordering(self):
        assert ability_component(ABILITY_STRONG) > ability_component(ABILITY_UNKNOWN) \
            > ability_component(ABILITY_WEAK)


# ── Actions ─────────────────────────────────────────────────────────────────

class TestRecommendedAction:
    def test_stage_ladder(self):
        assert recommended_action(0, ABILITY_UNKNOWN) == "NONE"
        assert recommended_action(3, ABILITY_STRONG) == "SELF_CURE_WATCH"
        assert recommended_action(20, ABILITY_STRONG) == "SOFT_REMINDER"
        assert recommended_action(45, ABILITY_STRONG) == "PRIORITY_CALL"
        assert recommended_action(120, ABILITY_STRONG) == "FIELD_VISIT"
        assert recommended_action(200, ABILITY_STRONG) == "LEGAL_REVIEW"

    def test_weak_ability_gets_restructure_not_pressure(self):
        assert recommended_action(45, ABILITY_WEAK) == "RESTRUCTURE_OFFER"
        assert recommended_action(120, ABILITY_WEAK) == "RESTRUCTURE_OFFER"


# ── Composite ───────────────────────────────────────────────────────────────

class TestCompositePriority:
    def test_score_bounded_0_100(self):
        worst = collections_priority(1.0, 75, 10_000_000, broken_ptp_count=3,
                                     features=MPESA_STRONG)
        assert worst.priority_score <= 100.0
        best = collections_priority(0.0, 0, 0, fulfilled_ptp_count=3, features=MPESA_WEAK)
        assert best.priority_score >= 0.0

    def test_band_is_lms_enum(self):
        r = collections_priority(0.3, 45, 30_000)
        assert r.priority_band in PRIORITY_BANDS

    def test_high_risk_mid_stage_big_exposure_is_critical(self):
        r = collections_priority(0.85, 75, 500_000, broken_ptp_count=2)
        assert r.priority_band == "CRITICAL"

    def test_low_risk_early_small_is_low_or_normal(self):
        r = collections_priority(0.03, 3, 2_000, fulfilled_ptp_count=2, features=MPESA_WEAK)
        assert r.priority_band in ("LOW", "NORMAL")

    def test_monotonic_in_pd(self):
        lo = collections_priority(0.1, 45, 50_000).priority_score
        hi = collections_priority(0.6, 45, 50_000).priority_score
        assert hi > lo

    def test_components_sum_to_score(self):
        r = collections_priority(0.4, 45, 80_000, broken_ptp_count=1)
        assert r.priority_score == pytest.approx(sum(r.components.values()), abs=0.01)

    def test_cutoff_env_override(self, monkeypatch):
        monkeypatch.setenv("COLLECTIONS_CUTOFF_CRITICAL", "10")
        assert band_cutoffs()["CRITICAL"] == 10.0
        r = collections_priority(0.2, 20, 20_000)
        assert r.priority_band == "CRITICAL"

    def test_broken_promises_outrank_kept_promises(self):
        broken = collections_priority(0.3, 45, 50_000, broken_ptp_count=2)
        kept = collections_priority(0.3, 45, 50_000, fulfilled_ptp_count=2)
        assert broken.priority_score > kept.priority_score
