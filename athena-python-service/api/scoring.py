from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import verify_jwt
from db.database import get_db

router = APIRouter()


class ScoreSummaryResponse(BaseModel):
    customer_id: int
    final_score: Optional[int]
    score_band: Optional[str]
    pd_probability: Optional[float]
    scored_at: Optional[str]


class FullReportResponse(BaseModel):
    customer_id: int
    customer_name: Optional[str]
    final_score: Optional[int]
    score_band: Optional[str]
    base_score: Optional[float]
    crb_contribution: Optional[float]
    llm_adjustment: Optional[int]
    pd_probability: Optional[float]
    reasoning: Optional[str]
    crb_name: Optional[str]
    bureau_score: Optional[int]
    scored_at: Optional[str]


@router.get("/credit-score/{customer_id}", response_model=ScoreSummaryResponse)
async def get_latest_score(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt),
):
    """Returns the latest credit score summary for a customer."""
    _check_access(claims, customer_id)
    row = await db.execute(text("""
        SELECT final_score, score_band, pd_probability, scored_at
        FROM credit_score_events WHERE customer_id = :cid
        ORDER BY scored_at DESC LIMIT 1
    """), {"cid": customer_id})
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="No score found for customer")
    return ScoreSummaryResponse(
        customer_id=customer_id,
        final_score=r[0], score_band=r[1],
        pd_probability=r[2], scored_at=str(r[3]),
    )


@router.get("/credit-report/{customer_id}", response_model=FullReportResponse)
async def get_full_report(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt),
):
    """Returns the full credit report for a customer (portals + third-party)."""
    _check_access(claims, customer_id)
    row = await db.execute(text("""
        SELECT
          c.first_name || ' ' || c.last_name AS customer_name,
          cse.final_score, cse.score_band, cse.base_score,
          cse.crb_contribution, cse.llm_adjustment,
          cse.pd_probability, cse.reasoning, cse.scored_at,
          cr.crb_name, cr.bureau_score
        FROM credit_score_events cse
        JOIN customers c ON c.customer_id = cse.customer_id
        LEFT JOIN crb_reports cr ON cr.report_id = cse.crb_report_id
        WHERE cse.customer_id = :cid
        ORDER BY cse.scored_at DESC LIMIT 1
    """), {"cid": customer_id})
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="No report found")
    return FullReportResponse(
        customer_id=customer_id,
        customer_name=r[0], final_score=r[1], score_band=r[2],
        base_score=r[3], crb_contribution=r[4], llm_adjustment=r[5],
        pd_probability=r[6], reasoning=r[7], scored_at=str(r[8]),
        crb_name=r[9], bureau_score=r[10],
    )


def _check_access(claims: dict, customer_id: int):
    """Customers can only view their own report; admins can view all."""
    roles: List[str] = claims.get("roles", [])
    token_customer_id = claims.get("customerId")
    is_admin = any(r in roles for r in ("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK"))
    if not is_admin and str(token_customer_id) != str(customer_id):
        raise HTTPException(status_code=403, detail="Access denied")
