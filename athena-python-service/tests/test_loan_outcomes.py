"""
Tests for listeners/loan_outcomes.py — LMS event → training label mapping,
FlexibleCustomerID replication, and the upsert path.
"""
import asyncio
import json
from datetime import datetime, timezone

from listeners.loan_outcomes import (
    _handle_body,
    flexible_customer_id,
    map_event_to_label,
    upsert_label,
)


# ── FlexibleCustomerID replication ───────────────────────────────────────────

class TestFlexibleCustomerId:
    def test_numeric_string_parses(self):
        assert flexible_customer_id("12345") == 12345

    def test_empty_is_zero(self):
        assert flexible_customer_id("") == 0

    def test_short_hash_matches_exact_java_style_value(self):
        # "CUST-1": h = ((((67*31+85)*31+83)*31+84)*31+45)*31+49 — no int64
        # wrap and < 2^53, so the float64 round-trip is exact.
        expected = 0
        for ch in "CUST-1":
            expected = expected * 31 + ord(ch)
        assert flexible_customer_id("CUST-1") == expected == 1999207223

    def test_long_ids_are_deterministic_and_non_negative(self):
        a = flexible_customer_id("EODINT-2026-07-20-000042")
        b = flexible_customer_id("EODINT-2026-07-20-000042")
        assert a == b
        assert a >= 0

    def test_different_ids_differ(self):
        assert flexible_customer_id("CUST-001") != flexible_customer_id("CUST-002")


# ── Event → label mapping ────────────────────────────────────────────────────

def payload(**overrides):
    base = {
        "loanId": "b7f8a5f2-0000-4000-8000-000000000001",
        "tenantId": "nemo",
        "customerId": "CUST-001",
        "status": "CLOSED",
        "stage": "PERFORMING",
        "dpd": 0,
        "timestamp": "2026-07-20T10:00:00Z",
    }
    base.update(overrides)
    return base


class TestMapEventToLabel:
    def test_written_off_is_default(self):
        label = map_event_to_label("loan.written.off", payload(status="WRITTEN_OFF"))
        assert label["default_flag"] == 1
        assert label["event_type"] == "loan.written.off"
        assert label["source"] == "LMS_EVENT"

    def test_closed_on_time_is_good(self):
        label = map_event_to_label("loan.closed", payload())
        assert label["default_flag"] == 0

    def test_closed_with_default_status_is_bad(self):
        assert map_event_to_label("loan.closed", payload(status="DEFAULT"))["default_flag"] == 1
        assert map_event_to_label("loan.closed", payload(status="DEFAULTED"))["default_flag"] == 1

    def test_closed_deep_delinquent_is_bad_even_if_settled(self):
        assert map_event_to_label("loan.closed", payload(dpd=120))["default_flag"] == 1

    def test_closed_mildly_late_is_good(self):
        assert map_event_to_label("loan.closed", payload(dpd=15))["default_flag"] == 0

    def test_stage_loss_is_terminal_bad(self):
        label = map_event_to_label(
            "loan.stage.changed", payload(newStage="LOSS", stage="LOSS")
        )
        assert label["default_flag"] == 1

    def test_non_terminal_stage_change_ignored(self):
        assert map_event_to_label(
            "loan.stage.changed", payload(newStage="WATCH", stage="WATCH")
        ) is None

    def test_unrelated_event_ignored(self):
        assert map_event_to_label("payment.completed", payload()) is None

    def test_missing_loan_id_ignored(self):
        assert map_event_to_label("loan.closed", payload(loanId="")) is None

    def test_missing_customer_id_ignored(self):
        assert map_event_to_label("loan.closed", payload(customerId=None)) is None

    def test_customer_id_hashed_like_lms(self):
        label = map_event_to_label("loan.closed", payload(customerId="CUST-1"))
        assert label["customer_id"] == 1999207223

    def test_numeric_customer_id_passthrough(self):
        label = map_event_to_label("loan.closed", payload(customerId=42))
        assert label["customer_id"] == 42

    def test_observed_at_prefers_closed_at(self):
        label = map_event_to_label(
            "loan.closed",
            payload(closedAt="2026-06-01T08:30:00Z", timestamp="2026-07-20T10:00:00Z"),
        )
        assert label["observed_at"] == datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)

    def test_envelope_timestamp_fallback_with_nanos(self):
        label = map_event_to_label(
            "loan.written.off",
            payload(timestamp=None, closedAt=None),
            envelope_ts="2026-07-20T10:00:00.123456789Z",
        )
        assert label["observed_at"].year == 2026
        assert label["observed_at"].microsecond == 123456

    def test_tenant_from_payload(self):
        assert map_event_to_label("loan.closed", payload())["tenant_id"] == "nemo"
        assert map_event_to_label(
            "loan.closed", payload(tenantId="acme")
        )["tenant_id"] == "acme"


# ── Upsert + end-to-end message handling (fake DB session) ───────────────────

class FakeSession:
    def __init__(self):
        self.executed = []
        self.commits = 0

    async def execute(self, sql, params=None):
        self.executed.append((str(sql), params))

    async def commit(self):
        self.commits += 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class TestUpsert:
    def test_upsert_sql_and_params(self):
        db = FakeSession()
        label = map_event_to_label("loan.written.off", payload())
        asyncio.run(upsert_label(db, label))
        assert db.commits == 1
        sql, params = db.executed[0]
        assert "INSERT INTO training_labels" in sql
        assert "ON CONFLICT (loan_ref, event_type) DO UPDATE" in sql
        assert params["loan_ref"] == payload()["loanId"]
        assert params["default_flag"] == 1
        assert params["source"] == "LMS_EVENT"


def envelope(routing_key, pl):
    return json.dumps({
        "id": "evt-1", "type": routing_key, "version": 1,
        "source": "loan-management-service", "tenantId": "nemo",
        "timestamp": "2026-07-20T10:00:00.5Z",
        "payload": pl,
    }).encode()


class TestHandleBody:
    def test_terminal_event_lands_in_db(self):
        db = FakeSession()
        asyncio.run(_handle_body(
            envelope("loan.closed", payload(status="DEFAULT")), "loan.closed", lambda: db
        ))
        assert db.commits == 1
        assert db.executed[0][1]["default_flag"] == 1

    def test_non_terminal_event_writes_nothing(self):
        db = FakeSession()
        asyncio.run(_handle_body(
            envelope("loan.disbursed", payload()), "loan.disbursed", lambda: db
        ))
        assert db.executed == []

    def test_garbage_body_is_dropped(self):
        db = FakeSession()
        asyncio.run(_handle_body(b"not json", "loan.closed", lambda: db))
        assert db.executed == []

    def test_double_encoded_payload_tolerated(self):
        db = FakeSession()
        body = json.dumps({
            "type": "loan.written.off", "tenantId": "nemo",
            "timestamp": "2026-07-20T10:00:00Z",
            "payload": json.dumps(payload()),
        }).encode()
        asyncio.run(_handle_body(body, "loan.written.off", lambda: db))
        assert db.commits == 1
