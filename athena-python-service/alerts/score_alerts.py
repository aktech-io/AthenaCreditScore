from __future__ import annotations

"""
Score-change alerts (NemoScore Phase 4, contract 1.5.0).

After every repeat scoring run, compare the new score against the customer's
previous SCORED event and — when it moved bands or by at least the alert
threshold — persist a `score_alerts` row (the portal Alerts feed) and publish
a SCORE_UPDATED event to athena.exchange → athena.notification.queue, where
notification-service turns it into an email (SMS once configured).

Design points:
- The alert row is persisted FIRST and unconditionally on a qualifying change;
  the AMQP publish is best-effort (`notified` records whether it went out).
  A RabbitMQ outage never loses the alert from the customer's feed.
- Per-customer opt-out + threshold override live in `alert_preferences`
  (absent row = enabled, service default threshold SCORE_ALERT_MIN_DELTA=10 —
  matching the portal's advertised default).
- Only SCORED→SCORED transitions alert: INSUFFICIENT_DATA runs are not score
  changes, and a first-ever score has nothing to compare against.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Go pkg/athena/rabbitmq topology (client.go) — must stay in sync.
EXCHANGE = "athena.exchange"
NOTIFICATION_ROUTING_KEY = "athena.notification.routingKey"

REASON_BAND_CHANGE = "BAND_CHANGE"
REASON_SCORE_DELTA = "SCORE_DELTA"


def min_delta_default() -> int:
    """Alert threshold in score points. Override: SCORE_ALERT_MIN_DELTA."""
    return int(os.getenv("SCORE_ALERT_MIN_DELTA", "10"))


def should_alert(
    previous_score: int,
    new_score: int,
    previous_band: Optional[str],
    new_band: Optional[str],
    min_delta: int,
) -> Optional[str]:
    """Returns the alert reason, or None when the change is not alert-worthy.
    Band changes always alert (they move pricing); otherwise the absolute
    point delta must reach min_delta."""
    if previous_band and new_band and previous_band != new_band:
        return REASON_BAND_CHANGE
    if abs(int(new_score) - int(previous_score)) >= max(1, int(min_delta)):
        return REASON_SCORE_DELTA
    return None


@dataclass
class ScoreAlert:
    alert_id: int
    customer_id: int
    reason: str
    previous_score: int
    new_score: int
    delta: int
    previous_band: Optional[str]
    new_band: Optional[str]


async def _previous_scored_event(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    """Most recent SCORED event *before* the latest one (which is the run
    that just persisted). None on first-ever scores or all-thin history."""
    rows = await db.execute(text("""
        SELECT final_score, score_band, status FROM credit_score_events
        WHERE customer_id = :cid
        ORDER BY scored_at DESC OFFSET 1 LIMIT 10
    """), {"cid": customer_id})
    for r in rows.fetchall():
        status = r[2] or "SCORED"  # legacy rows pre-date the status column
        if status == "SCORED" and r[0] is not None:
            return {"score": int(float(r[0])), "band": r[1]}
    return None


async def _preferences(db: AsyncSession, customer_id: int) -> Dict[str, Any]:
    row = await db.execute(text("""
        SELECT score_change_enabled, min_delta FROM alert_preferences
        WHERE customer_id = :cid
    """), {"cid": customer_id})
    r = row.fetchone()
    if not r:
        return {"enabled": True, "min_delta": min_delta_default()}
    return {
        "enabled": bool(r[0]),
        "min_delta": int(r[1]) if r[1] is not None else min_delta_default(),
    }


async def _publish_notification(payload: Dict[str, Any]) -> bool:
    """Best-effort publish to the shared notification queue. Returns success."""
    url = os.getenv("RABBITMQ_URL")
    if not url:
        return False
    try:
        import aio_pika
        connection = await aio_pika.connect_robust(url, timeout=5)
        try:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=NOTIFICATION_ROUTING_KEY,
            )
        finally:
            await connection.close()
        return True
    except Exception as exc:
        logger.warning("SCORE_UPDATED publish failed", error=str(exc))
        return False


async def process_score_change(
    db: AsyncSession,
    customer_id: int,
    tenant_id: str,
    new_score: Optional[int],
    new_band: Optional[str],
    new_status: str,
) -> Optional[ScoreAlert]:
    """Called after a scoring run has committed its score event. Never raises —
    alerting must not break scoring."""
    try:
        if new_status != "SCORED" or new_score is None:
            return None

        previous = await _previous_scored_event(db, customer_id)
        if previous is None:
            return None

        prefs = await _preferences(db, customer_id)
        if not prefs["enabled"]:
            return None

        reason = should_alert(
            previous["score"], new_score, previous["band"], new_band, prefs["min_delta"]
        )
        if reason is None:
            return None

        delta = int(new_score) - previous["score"]
        inserted = await db.execute(text("""
            INSERT INTO score_alerts
                (customer_id, tenant_id, reason, previous_score, new_score,
                 delta, previous_band, new_band)
            VALUES (:cid, :tenant, :reason, :prev, :new, :delta, :pband, :nband)
            RETURNING alert_id
        """), {
            "cid": customer_id, "tenant": tenant_id, "reason": reason,
            "prev": previous["score"], "new": int(new_score), "delta": delta,
            "pband": previous["band"], "nband": new_band,
        })
        alert_id = inserted.scalar()
        await db.commit()

        contact = await db.execute(text("""
            SELECT email, mobile_number FROM customers WHERE customer_id = :cid
        """), {"cid": customer_id})
        c = contact.fetchone()
        email = (c[0] or "") if c else ""
        mobile = (c[1] or "") if c else ""

        published = await _publish_notification({
            "type": "SCORE_UPDATED",
            "customerId": customer_id,
            "email": email,
            "mobile": mobile,
            "score": int(new_score),
            "previousScore": previous["score"],
            "delta": delta,
            "band": new_band,
            "previousBand": previous["band"],
            "reason": reason,
            "tenantId": tenant_id,
        })
        if published:
            await db.execute(text(
                "UPDATE score_alerts SET notified = TRUE WHERE alert_id = :aid"
            ), {"aid": alert_id})
            await db.commit()

        logger.info(
            "Score-change alert",
            customer_id=customer_id, reason=reason, delta=delta,
            previous=previous["score"], new=int(new_score), notified=published,
        )
        return ScoreAlert(
            alert_id=alert_id, customer_id=customer_id, reason=reason,
            previous_score=previous["score"], new_score=int(new_score),
            delta=delta, previous_band=previous["band"], new_band=new_band,
        )
    except Exception as exc:
        logger.warning("Score-change alerting failed", customer_id=customer_id, error=str(exc))
        return None
