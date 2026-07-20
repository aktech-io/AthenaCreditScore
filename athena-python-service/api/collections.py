from __future__ import annotations

"""
Collections-priority endpoint (contract: docs/nemoscore-api.yaml 1.5.0):

  POST /api/v1/credit-score/{customer_id}/collections-priority

Called by the LMS collections-service when a case opens or its DPD changes.
The LMS supplies the operational state only it knows (DPD, outstanding,
promise-to-pay history); NemoScore contributes the borrower's PD and
cash-flow ability-to-pay. Fail-loud like the other decisioning endpoints:
404 when no score exists, 409 on INSUFFICIENT_DATA — in both cases the LMS
keeps its existing DPD-threshold prioritization.
"""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.decisioning import _latest_score_event
from api.scoring import _check_access
from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db
from scoring.collections_priority import collections_priority

logger = structlog.get_logger(__name__)
router = APIRouter()


class CollectionsPriorityRequest(BaseModel):
    dpd: int = Field(ge=0, description="Current days past due")
    outstanding_amount: float = Field(ge=0, description="Outstanding balance, KES")
    broken_ptp_count: int = Field(default=0, ge=0,
                                  description="Broken promises to pay on this case")
    fulfilled_ptp_count: int = Field(default=0, ge=0,
                                     description="Fulfilled promises to pay on this case")
    product_type: Optional[str] = Field(default=None, description="Echoed back; not scored")


@router.post("/credit-score/{customer_id}/collections-priority")
async def post_collections_priority(
    customer_id: int,
    body: CollectionsPriorityRequest,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Collections-priority score for a delinquent case. Added in 1.5.0."""
    _check_access(claims, customer_id)

    event = await _latest_score_event(db, customer_id)
    if event is None or event["score"] is None:
        raise HTTPException(status_code=404, detail="No score found for customer — score first")
    if event["status"] == "INSUFFICIENT_DATA":
        raise HTTPException(
            status_code=409,
            detail="Latest score is INSUFFICIENT_DATA — keep DPD-based prioritization",
        )

    # Cash-flow ability-to-pay is best-effort: without features the ability
    # signal degrades to UNKNOWN, the rest of the score still stands.
    try:
        from features.pipeline import get_or_compute_features
        features = await get_or_compute_features(db, customer_id)
    except Exception:
        features = None

    result = collections_priority(
        pd_probability=event["pd"],
        dpd=body.dpd,
        outstanding_amount=body.outstanding_amount,
        broken_ptp_count=body.broken_ptp_count,
        fulfilled_ptp_count=body.fulfilled_ptp_count,
        features=features,
    )

    logger.info(
        "Collections priority computed",
        customer_id=customer_id, dpd=body.dpd,
        priority_score=result.priority_score, priority_band=result.priority_band,
    )
    return {
        "customer_id": customer_id,
        "currency": "KES",
        "product_type": body.product_type,
        "dpd": body.dpd,
        "outstanding_amount": round(float(body.outstanding_amount), 2),
        **asdict(result),
        "final_score": event["score"],
        "pd_probability": round(event["pd"], 6),
        "scored_at": event["scored_at"],
    }
