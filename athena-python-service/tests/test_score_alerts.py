"""
Phase 4 — score-change alert decision tests (pure logic in
alerts/score_alerts.py; the persist/publish path is live-verified against the
running stack, mirroring the decisioning test split).
"""

from alerts.score_alerts import (
    REASON_BAND_CHANGE,
    REASON_SCORE_DELTA,
    min_delta_default,
    should_alert,
)


class TestShouldAlert:
    def test_band_change_always_alerts(self):
        assert should_alert(700, 705, "Good", "Very Good", 10) == REASON_BAND_CHANGE

    def test_band_change_wins_over_delta(self):
        # Both conditions true → reported as the band change (it moves pricing).
        assert should_alert(650, 700, "Fair", "Good", 10) == REASON_BAND_CHANGE

    def test_delta_at_threshold_alerts(self):
        assert should_alert(700, 710, "Good", "Good", 10) == REASON_SCORE_DELTA
        assert should_alert(700, 690, "Good", "Good", 10) == REASON_SCORE_DELTA

    def test_delta_below_threshold_is_quiet(self):
        assert should_alert(700, 709, "Good", "Good", 10) is None
        assert should_alert(700, 691, "Good", "Good", 10) is None

    def test_no_change_is_quiet(self):
        assert should_alert(700, 700, "Good", "Good", 10) is None

    def test_negative_delta_uses_absolute_value(self):
        assert should_alert(700, 680, "Good", "Good", 15) == REASON_SCORE_DELTA

    def test_missing_bands_fall_back_to_delta(self):
        assert should_alert(700, 720, None, "Very Good", 10) == REASON_SCORE_DELTA
        assert should_alert(700, 705, None, None, 10) is None

    def test_min_delta_floor_is_one(self):
        # A zero/negative threshold must not alert on identical scores.
        assert should_alert(700, 700, "Good", "Good", 0) is None
        assert should_alert(700, 701, "Good", "Good", 0) == REASON_SCORE_DELTA


class TestMinDeltaDefault:
    def test_default_is_ten(self, monkeypatch):
        monkeypatch.delenv("SCORE_ALERT_MIN_DELTA", raising=False)
        assert min_delta_default() == 10

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("SCORE_ALERT_MIN_DELTA", "25")
        assert min_delta_default() == 25
