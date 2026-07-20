from __future__ import annotations

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db

router = APIRouter()


class ScoreSummaryResponse(BaseModel):
    customer_id: int
    final_score: Optional[int]
    score_band: Optional[str]
    pd_probability: Optional[float]
    scored_at: Optional[str]
    status: str
    data_sufficiency: str = "FULL"
    pd_source: Optional[str] = None
    model_version: Optional[str] = None


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
    reason_codes: List[Dict[str, str]] = []


@router.get("/credit-score/{customer_id}", response_model=ScoreSummaryResponse)
async def get_latest_score(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Returns the latest credit score summary for a customer."""
    _check_access(claims, customer_id)
    row = await db.execute(text("""
        SELECT final_score, score_band, pd_probability, scored_at,
               status, data_sufficiency, pd_source, model_version
        FROM credit_score_events WHERE customer_id = :cid
        ORDER BY scored_at DESC LIMIT 1
    """), {"cid": customer_id})
    r = row.fetchone()
    if not r:
        # Score-on-miss for service callers only (the LMS sends hashed int64
        # ids NemoScore has never seen — see docs/nemo/06 integration notes).
        # The result is honest: with no transactions and no bureau data the
        # scorer returns status=INSUFFICIENT_DATA, which the LMS maps to
        # SKIPPED/manual review instead of a hard FAILED on 404.
        roles: List[str] = claims.get("roles", [])
        if not any(rl in roles for rl in ("SERVICE", "ADMIN", "ANALYST")):
            raise HTTPException(status_code=404, detail="No score found for customer")
        return await _score_on_miss(db, customer_id)
    return ScoreSummaryResponse(
        customer_id=customer_id,
        final_score=r[0], score_band=r[1],
        pd_probability=r[2], scored_at=str(r[3]),
        status=r[4], data_sufficiency=r[5],
        pd_source=r[6], model_version=r[7],
    )


async def _score_on_miss(db: AsyncSession, customer_id: int) -> ScoreSummaryResponse:
    """First-touch scoring for a customer with no stored score event.

    Creates a placeholder customer row when the id is unknown (LMS hashed ids),
    scores from whatever data exists (usually none), and persists the event so
    subsequent GETs are plain reads.
    """
    from scoring.hybrid_scorer import compute_hybrid_score

    await db.execute(text("""
        INSERT INTO customers (customer_id, first_name, last_name)
        VALUES (:cid, 'EXTERNAL', 'UNREGISTERED')
        ON CONFLICT (customer_id) DO NOTHING
    """), {"cid": customer_id})

    tx_rows = await db.execute(text("""
        SELECT transaction_date, amount, transaction_type, category,
               description, channel, balance_after
        FROM transactions WHERE customer_id = :cid
        ORDER BY transaction_date DESC LIMIT 500
    """), {"cid": customer_id})
    transactions = [dict(t._mapping) for t in tx_rows.fetchall()]

    features = None
    try:
        from features.pipeline import get_or_compute_features
        features = await get_or_compute_features(db, customer_id)
    except Exception:
        pass  # scorecard fallback covers the no-vector case

    result = await compute_hybrid_score(
        customer_id=customer_id,
        customer_name="EXTERNAL UNREGISTERED",
        transactions=transactions,
        crb_raw_report=None,
        features=features,
    )

    import json as _json
    inserted = await db.execute(text("""
        INSERT INTO credit_score_events
          (customer_id, base_score, crb_contribution, llm_adjustment,
           pd_probability, final_score, score_band, reasoning,
           llm_provider, llm_model_name, model_target, reason_codes,
           status, data_sufficiency, pd_source, model_version)
        VALUES (:cid, :base, :crb, :llm, :pd, :final, :band, :reasoning,
                :llm_prov, :llm_mod, :target, CAST(:rcodes AS jsonb),
                :status, :sufficiency, :pd_source, :model_version)
        RETURNING scored_at
    """), {
        "cid": customer_id,
        "base": result.base_score,
        "crb": result.crb_contribution,
        "llm": result.llm_adjustment,
        "pd": result.pd_probability,
        "final": result.final_score,
        "band": result.score_band,
        "reasoning": "\n".join(result.reasoning),
        "llm_prov": result.llm_provider,
        "llm_mod": result.llm_model,
        "target": result.model_target,
        "rcodes": _json.dumps(result.reason_codes),
        "status": result.status,
        "sufficiency": result.data_sufficiency,
        "pd_source": result.pd_source,
        "model_version": result.model_version,
    })
    scored_at = inserted.scalar()
    await db.commit()

    return ScoreSummaryResponse(
        customer_id=customer_id,
        final_score=result.final_score,
        score_band=result.score_band,
        pd_probability=result.pd_probability,
        scored_at=str(scored_at),
        status=result.status,
        data_sufficiency=result.data_sufficiency,
        pd_source=result.pd_source,
        model_version=result.model_version,
    )


@router.get("/credit-report/{customer_id}", response_model=FullReportResponse)
async def get_full_report(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Returns the full credit report for a customer (portals + third-party)."""
    _check_access(claims, customer_id)
    row = await db.execute(text("""
        SELECT
          c.first_name || ' ' || c.last_name AS customer_name,
          cse.final_score, cse.score_band, cse.base_score,
          cse.crb_contribution, cse.llm_adjustment,
          cse.pd_probability, cse.reasoning, cse.scored_at,
          cr.crb_name, cr.bureau_score, cse.reason_codes
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
        reason_codes=(r[11] if isinstance(r[11], list) else json.loads(r[11] or "[]")),
    )


def _check_access(claims: dict, customer_id: int):
    """Customers can only view their own report; admins can view all."""
    roles: List[str] = claims.get("roles", [])
    token_customer_id = claims.get("customerId")
    is_admin = any(r in roles for r in ("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK", "SERVICE"))
    if not is_admin and str(token_customer_id) != str(customer_id):
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("/credit-score/features/recompute")
async def recompute_features(
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Batch-recompute lgbm_features vectors (admin/service only)."""
    roles: List[str] = claims.get("roles", [])
    if not any(r in roles for r in ("ADMIN", "SERVICE")):
        raise HTTPException(status_code=403, detail="Admin or service role required")
    from features.pipeline import recompute_all_features
    count = await recompute_all_features(db)
    return {"recomputed": count}
