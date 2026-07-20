from __future__ import annotations

"""
LMS loan-outcome listener (NemoScore Phase 2 — real training labels).

Consumes loan lifecycle events from the LMS topic exchange
(`athena.lms.exchange`, see AthenaIntelligentLMS
go-services/internal/common/rabbitmq/topology.go) and upserts terminal
repayment outcomes into `training_labels`, which build_training_frame
(feedback/loop.py) prefers over the loans.status heuristic.

Wire format (go-services/internal/common/event/domain_event.go):

    {
      "id": "<uuid>", "type": "loan.closed", "version": 1,
      "source": "loan-management-service", "tenantId": "nemo",
      "correlationId": "<loanId>", "timestamp": "2026-07-20T10:00:00.123Z",
      "payload": { "loanId": "...", "customerId": "CUST-001", "status": "...",
                   "stage": "...", "dpd": 0, ... }
    }

Routing key == event type. Events consumed:

    loan.written.off   → default_flag 1  (terminal loss)
    loan.closed        → 1 if status DEFAULT*/WRITTEN_OFF or dpd >= DEFAULT_DPD,
                         else 0 (settled on time)
    loan.stage.changed → 1 only when newStage is LOSS (IFRS-9 terminal bucket);
                         all other stage moves are non-terminal → ignored

Identity: LMS customer ids are varchar (CUST-…, EODINT-…). The LMS
ai-scoring service coerces them to int64 with FlexibleCustomerID
(go-services/internal/scoring/model/model.go) before calling NemoScore, so
labels MUST key on the same coercion — replicated here bit-for-bit,
including the Go int64 wrap-around and the float64 round-trip in
`int64(math.Abs(float64(h)))`.

Resilience: the listener runs as a background asyncio task. If RABBITMQ_URL
is unset it is skipped with a log line. Broker/exchange not up yet, or any
consume error → retry with capped exponential backoff; it never crashes the
app.
"""

import asyncio
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)

# Topology constants — must match LMS LmsRabbitMQConfig / topology.go.
LMS_EXCHANGE = "athena.lms.exchange"
QUEUE_NAME = "nemoscore.training.labels.queue"
ROUTING_KEYS = ("loan.closed", "loan.written.off", "loan.stage.changed")

# A loan closed while 90+ days past due is a default by Basel/CBK convention,
# even if it eventually settled.
DEFAULT_DPD = int(os.getenv("LABEL_DEFAULT_DPD", "90"))

_BAD_STATUSES = ("DEFAULT", "DEFAULTED", "WRITTEN_OFF", "WRITE_OFF")
_TERMINAL_BAD_STAGES = ("LOSS",)

_INT64_MASK = (1 << 64) - 1
_INT64_MIN = -(1 << 63)


def _wrap64(v: int) -> int:
    """Interpret an unbounded int as Go's wrapping signed 64-bit int."""
    v &= _INT64_MASK
    return v - (1 << 64) if v >= (1 << 63) else v


def flexible_customer_id(raw: str) -> int:
    """
    Replicate LMS FlexibleCustomerID (go-services/internal/scoring/model/
    model.go): all-digit strings parse as int64; anything else is hashed with
    h = h*31 + rune (wrapping int64), then int64(math.Abs(float64(h))).
    """
    if not raw:
        return 0
    n = 0
    for c in raw:
        if "0" <= c <= "9":
            n = _wrap64(n * 10 + (ord(c) - ord("0")))
        else:
            h = 0
            for ch in raw:
                h = _wrap64(h * 31 + ord(ch))
            # Go: int64(math.Abs(float64(h))) — float64 rounding included.
            f = abs(float(h))
            if f >= float(1 << 63):
                # Out-of-range float→int64 conversion yields MinInt64 on amd64.
                return _INT64_MIN
            return int(f)
    return n


def _parse_ts(value: Any) -> Optional[datetime]:
    """Parse RFC3339(Nano) timestamps as emitted by the Go services."""
    if not isinstance(value, str) or not value:
        return None
    s = value.strip().replace("Z", "+00:00")
    # Truncate fractional seconds to 6 digits for fromisoformat.
    s = re.sub(r"\.(\d{6})\d+", r".\1", s)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def map_event_to_label(
    routing_key: str,
    payload: Dict[str, Any],
    tenant_id: str = "nemo",
    envelope_ts: Any = None,
) -> Optional[Dict[str, Any]]:
    """
    Map an LMS loan lifecycle event to a training label row, or None when the
    event carries no terminal repayment outcome.
    """
    loan_ref = str(payload.get("loanId") or "").strip()
    raw_customer = payload.get("customerId")
    if not loan_ref or raw_customer in (None, ""):
        return None

    customer_id = (
        int(raw_customer)
        if isinstance(raw_customer, (int, float)) and not isinstance(raw_customer, bool)
        else flexible_customer_id(str(raw_customer))
    )
    if customer_id == 0:
        return None

    status = str(payload.get("status") or "").upper()
    dpd = _as_int(payload.get("dpd"))

    if routing_key == "loan.written.off":
        default_flag = 1
    elif routing_key == "loan.closed":
        bad_status = any(status.startswith(b) for b in _BAD_STATUSES)
        default_flag = 1 if (bad_status or dpd >= DEFAULT_DPD) else 0
    elif routing_key == "loan.stage.changed":
        new_stage = str(payload.get("newStage") or payload.get("stage") or "").upper()
        if new_stage not in _TERMINAL_BAD_STAGES:
            return None
        default_flag = 1
    else:
        return None

    observed_at = (
        _parse_ts(payload.get("closedAt"))
        or _parse_ts(payload.get("timestamp"))
        or _parse_ts(envelope_ts)
        or datetime.now(timezone.utc)
    )

    return {
        "customer_id": customer_id,
        "loan_ref": loan_ref,
        "event_type": routing_key,
        "default_flag": default_flag,
        "observed_at": observed_at,
        "tenant_id": (payload.get("tenantId") or tenant_id or "nemo"),
        "source": "LMS_EVENT",
    }


UPSERT_SQL = text("""
    INSERT INTO training_labels
        (customer_id, loan_ref, event_type, default_flag, observed_at, tenant_id, source)
    VALUES
        (:customer_id, :loan_ref, :event_type, :default_flag, :observed_at, :tenant_id, :source)
    ON CONFLICT (loan_ref, event_type) DO UPDATE SET
        default_flag = EXCLUDED.default_flag,
        observed_at  = EXCLUDED.observed_at,
        customer_id  = EXCLUDED.customer_id,
        tenant_id    = EXCLUDED.tenant_id
""")


async def upsert_label(db, label: Dict[str, Any]) -> None:
    await db.execute(UPSERT_SQL, label)
    await db.commit()


async def _handle_body(body: bytes, routing_key: str, session_factory) -> None:
    try:
        envelope = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        logger.warning("Undecodable LMS event dropped", routing_key=routing_key)
        return

    event_type = envelope.get("type") or routing_key
    payload = envelope.get("payload")
    if isinstance(payload, str):  # tolerate double-encoded payloads
        try:
            payload = json.loads(payload)
        except ValueError:
            payload = None
    if not isinstance(payload, dict):
        logger.warning("LMS event without object payload dropped", event_type=event_type)
        return

    label = map_event_to_label(
        event_type,
        payload,
        tenant_id=envelope.get("tenantId") or "nemo",
        envelope_ts=envelope.get("timestamp"),
    )
    if label is None:
        return

    async with session_factory() as db:
        await upsert_label(db, label)
    logger.info(
        "Training label recorded",
        loan_ref=label["loan_ref"],
        event_type=label["event_type"],
        customer_id=label["customer_id"],
        default_flag=label["default_flag"],
    )


async def run_listener(rabbitmq_url: str, session_factory=None) -> None:
    """Consume LMS loan events forever, reconnecting on any failure."""
    import aio_pika

    if session_factory is None:
        from db.database import AsyncSessionLocal
        session_factory = AsyncSessionLocal

    backoff = 5
    while True:
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=16)
                # Idempotent declare with the LMS's exact params (topic,
                # durable): works whether or not the LMS has started yet.
                exchange = await channel.declare_exchange(
                    LMS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
                )
                queue = await channel.declare_queue(QUEUE_NAME, durable=True)
                for key in ROUTING_KEYS:
                    await queue.bind(exchange, routing_key=key)
                logger.info(
                    "LMS loan-outcome listener consuming",
                    exchange=LMS_EXCHANGE, queue=QUEUE_NAME, keys=list(ROUTING_KEYS),
                )
                backoff = 5
                async with queue.iterator() as messages:
                    async for message in messages:
                        async with message.process(ignore_processed=True):
                            try:
                                await _handle_body(
                                    message.body, message.routing_key or "", session_factory
                                )
                            except Exception:
                                # Only transient failures reach here (DB down,
                                # connection reset) — _handle_body swallows
                                # malformed/non-terminal events without raising.
                                # Requeue once so an irreplaceable LMS outcome
                                # isn't silently lost; on the redelivery fall
                                # through to ack so nothing can poison-loop.
                                logger.exception(
                                    "Failed to process LMS event",
                                    routing_key=message.routing_key,
                                    redelivered=message.redelivered,
                                )
                                if not message.redelivered:
                                    await message.reject(requeue=True)
        except asyncio.CancelledError:
            logger.info("LMS loan-outcome listener stopped")
            raise
        except Exception as exc:
            logger.warning(
                "LMS loan-outcome listener error — retrying",
                error=str(exc), retry_in_s=backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 120)


def start_loan_outcomes_listener() -> Optional["asyncio.Task"]:
    """
    Startup hook for main.py lifespan. Returns the background task, or None
    when RABBITMQ_URL is not configured (listener skipped cleanly).
    """
    url = os.getenv("RABBITMQ_URL")
    if not url:
        logger.info("RABBITMQ_URL not set — LMS loan-outcome listener disabled")
        return None
    return asyncio.create_task(run_listener(url), name="lms-loan-outcomes-listener")


async def stop_loan_outcomes_listener(task: Optional["asyncio.Task"]) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
