"""
NemoScore — Reason code (adverse action) unit tests.

Covers both derivation paths in scoring/reason_codes.py:
- from_shap: ML path, SHAP contributions → codes
- from_scorecard: scorecard dimension deficits + bureau red flags → codes
"""
from dataclasses import dataclass, field

import pytest

from scoring.reason_codes import (
    FEATURE_TO_CODE,
    REASON_CODES,
    TOP_N,
    from_scorecard,
    from_shap,
)


# ── Test doubles matching the attributes reason_codes reads ─────────────────

@dataclass
class FakeBase:
    income_stability_score: float = 150.0
    avg_monthly_income_score: float = 150.0
    savings_rate_score: float = 100.0
    low_balance_score: float = 150.0
    transaction_diversity_score: float = 150.0


@dataclass
class FakeCrb:
    bureau_score: int = 700
    npa_count: int = 0
    active_defaults: int = 0
    enquiries_90d: int = 0
    applications_12m: int = 0


class TestFromShap:
    def test_positive_shap_maps_to_codes_most_severe_first(self):
        contribs = [
            ("bureau_score", 0.10),
            ("delinquency_rate_90d", 0.30),
            ("payment_cv", -0.05),          # protective — must not appear
            ("open_npa_accounts", 0.20),
        ]
        codes = [rc["code"] for rc in from_shap(contribs)]
        assert codes == ["NS10", "NS01", "NS03"]

    def test_caps_at_top_n(self):
        contribs = [(f, 1.0 - i * 0.1) for i, f in enumerate(FEATURE_TO_CODE)]
        assert len(from_shap(contribs)) == TOP_N

    def test_deduplicates_codes_sharing_a_feature_mapping(self):
        # total_loans and early_repayment_rate both map to NS13
        contribs = [("total_loans", 0.4), ("early_repayment_rate", 0.3)]
        out = from_shap(contribs)
        assert [rc["code"] for rc in out] == ["NS13"]

    def test_all_protective_yields_empty(self):
        assert from_shap([("bureau_score", -0.4), ("payment_cv", -0.1)]) == []

    def test_unmapped_features_skipped(self):
        assert from_shap([("mystery_feature", 0.9)]) == []

    def test_descriptions_come_from_registry(self):
        out = from_shap([("bureau_score", 0.5)])
        assert out[0]["description"] == REASON_CODES["NS03"]


class TestFromScorecard:
    def test_clean_profile_yields_no_codes(self):
        assert from_scorecard(FakeBase(), FakeCrb()) == []

    def test_bureau_red_flags_outrank_dimension_deficits(self):
        base = FakeBase(savings_rate_score=10.0)          # big deficit
        crb = FakeCrb(active_defaults=1, npa_count=2, bureau_score=480)
        codes = [rc["code"] for rc in from_scorecard(base, crb)]
        assert codes[:3] == ["NS02", "NS01", "NS03"]
        assert "NS07" in codes                            # deficit still reported

    def test_dimension_deficits_ranked_by_fraction_lost(self):
        base = FakeBase(
            income_stability_score=30.0,    # lost 80%
            savings_rate_score=60.0,        # lost 40%
            low_balance_score=140.0,        # lost <25% — below threshold
        )
        codes = [rc["code"] for rc in from_scorecard(base, None)]
        assert codes == ["NS05", "NS07"]

    def test_small_deficit_not_reported(self):
        base = FakeBase(transaction_diversity_score=120.0)  # lost 20% < 25%
        assert from_scorecard(base, None) == []

    def test_enquiry_pressure_flagged(self):
        codes = [rc["code"] for rc in from_scorecard(FakeBase(), FakeCrb(enquiries_90d=4))]
        assert codes == ["NS04"]

    def test_zero_bureau_score_is_not_low_score(self):
        # bureau_score == 0 means "no bureau data", not "terrible score"
        assert from_scorecard(FakeBase(), FakeCrb(bureau_score=0)) == []

    def test_caps_at_top_n(self):
        base = FakeBase(
            income_stability_score=0, avg_monthly_income_score=0,
            savings_rate_score=0, low_balance_score=0,
            transaction_diversity_score=0,
        )
        crb = FakeCrb(active_defaults=1, npa_count=1, bureau_score=400,
                      enquiries_90d=5)
        assert len(from_scorecard(base, crb)) == TOP_N

    def test_deterministic(self):
        base = FakeBase(savings_rate_score=20.0, low_balance_score=50.0)
        crb = FakeCrb(npa_count=1)
        assert from_scorecard(base, crb) == from_scorecard(base, crb)
