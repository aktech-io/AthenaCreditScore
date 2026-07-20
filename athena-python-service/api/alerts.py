from __future__ import annotations

"""
Score-change alert feed + preferences (contract: docs/nemoscore-api.yaml 1.5.0):

  GET /api/v1/credit-score/{customer_id}/alerts
  GET /api/v1/credit-score/{customer_id}/alerts/preferences
  PUT /api/v1/credit-score/{customer_id}/alerts/preferences

The feed backs the portal client Alerts page. Rows are written by
alerts/score_alerts.py on every alert-worthy scoring run — whether or not
the email/SMS notification went out (`notified` flags that).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from alerts.score_alerts import min_delta_default
from api.scoring import _check_access
from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db

router = APIRouter()


@router.get("/credit-score/{customer_id}/alerts")
async def get_alerts(
    customer_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Recent score-change alerts, newest first. Added in 1.5.0."""
    _check_access(claims, customer_id)
    rows = await db.execute(text("""
        SELECT alert_id, alert_type, reason, previous_score, new_score, delta,
               previous_band, new_band, notified, created_at
        FROM score_alerts
        WHERE customer_id = :cid
        ORDER BY created_at DESC
        LIMIT :lim
    """), {"cid": customer_id, "lim": limit})
    alerts = [{
        "alert_id": r[0],
        "alert_type": r[1],
        "reason": r[2],
        "previous_score": r[3],
        "new_score": r[4],
        "delta": r[5],
        "previous_band": r[6],
        "new_band": r[7],
        "notified": r[8],
        "created_at": str(r[9]),
    } for r in rows.fetchall()]
    return {"customer_id": customer_id, "count": len(alerts), "alerts": alerts}


class AlertPreferencesRequest(BaseModel):
    score_change_enabled: bool = Field(description="Receive score-change alerts")
    min_delta: Optional[int] = Field(
        default=None, ge=1, le=550,
        description="Minimum point change to alert on (null → service default; "
                    "band changes always alert)")


async def _read_preferences(db: AsyncSession, customer_id: int) -> dict:
    row = await db.execute(text("""
        SELECT score_change_enabled, min_delta FROM alert_preferences
        WHERE customer_id = :cid
    """), {"cid": customer_id})
    r = row.fetchone()
    return {
        "customer_id": customer_id,
        "score_change_enabled": bool(r[0]) if r else True,
        "min_delta": (r[1] if r and r[1] is not None else None),
        "effective_min_delta": (r[1] if r and r[1] is not None else min_delta_default()),
    }


@router.get("/credit-score/{customer_id}/alerts/preferences")
async def get_alert_preferences(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Per-customer alert preferences (absent row = defaults). Added in 1.5.0."""
    _check_access(claims, customer_id)
    return await _read_preferences(db, customer_id)


@router.put("/credit-score/{customer_id}/alerts/preferences")
async def put_alert_preferences(
    customer_id: int,
    body: AlertPreferencesRequest,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Upsert alert preferences. Added in 1.5.0."""
    _check_access(claims, customer_id)
    await db.execute(text("""
        INSERT INTO alert_preferences (customer_id, score_change_enabled, min_delta, updated_at)
        VALUES (:cid, :enabled, :delta, now())
        ON CONFLICT (customer_id) DO UPDATE SET
            score_change_enabled = EXCLUDED.score_change_enabled,
            min_delta = EXCLUDED.min_delta,
            updated_at = now()
    """), {"cid": customer_id, "enabled": body.score_change_enabled, "delta": body.min_delta})
    await db.commit()
    return await _read_preferences(db, customer_id)
