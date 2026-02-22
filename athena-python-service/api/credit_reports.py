from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from scoring.hybrid_scorer import compute_hybrid_score
from scoring.crb_extractor import extract_crb_metrics
from monitoring.metrics import SCORING_REQUESTS, SCORING_LATENCY
import time
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

# Simple API-key auth for inbound reports
VALID_API_KEYS = {"dev-key", "prod-key-placeholder"}


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ── Pydantic Models ─────────────────────────────────────────────────────────

class CustomerInfo(BaseModel):
    nationalId: str
    firstName: str
    lastName: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CreditReportPayload(BaseModel):
    customer: CustomerInfo
    creditReport: Dict[str, Any]


class ScoreResponse(BaseModel):
    customer_id: int
    base_score: float
    crb_contribution: float
    llm_adjustment: int
    pd_probability: float = Field(description="Probability of default (0-1)")
    final_score: int = Field(description="PDO-scaled score (300-850)")
    score_band: str
    reasoning: List[str]
    llm_provider: str
    llm_model: str
    scored_at: str


# ── Endpoint ────────────────────────────────────────────────────────────────

@router.post("/credit-reports", response_model=ScoreResponse)
async def ingest_credit_report(
    payload: CreditReportPayload,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    """
    Accepts an inbound credit report from a partner institution or CRB push.
    - Upserts the customer record.
    - Stores the CRB report.
    - Triggers hybrid credit score computation.
    - Returns the scored result.
    """
    start = time.perf_counter()

    national_id = payload.customer.nationalId

    # ── Upsert customer ──────────────────────────────────────────────────────
    existing = await db.execute(
        text("SELECT customer_id FROM customers WHERE national_id = :nid"),
        {"nid": national_id},
    )
    row = existing.fetchone()

    if row:
        customer_id = row[0]
    else:
        insert_result = await db.execute(text("""
            INSERT INTO customers (national_id, first_name, last_name, mobile_number, email, crb_consent)
            VALUES (:nid, :fn, :ln, :phone, :email, TRUE)
            RETURNING customer_id
        """), {
            "nid": national_id,
            "fn": payload.customer.firstName,
            "ln": payload.customer.lastName,
            "phone": payload.customer.phone,
            "email": payload.customer.email,
        })
        customer_id = insert_result.fetchone()[0]
        await db.commit()
        logger.info("New customer created from inbound report", customer_id=customer_id)

    crb_data = payload.creditReport
    report_date_str = crb_data.get("reportDate", str(date.today()))
    report_date = date.fromisoformat(report_date_str)
    bureau_name = crb_data.get("bureauName", "Unknown")

    # ── Store CRB report ────────────────────────────────────────────────────
    import json
    crb_metrics = extract_crb_metrics({"creditReport": crb_data})
    crb_insert = await db.execute(text("""
        INSERT INTO crb_reports (customer_id, crb_name, report_date, bureau_score, raw_report, extracted_metrics)
        VALUES (:cid, :name, :date, :score, CAST(:raw AS jsonb), CAST(:metrics AS jsonb))
        RETURNING report_id
    """), {
        "cid": customer_id,
        "name": bureau_name,
        "date": report_date,
        "score": crb_metrics.bureau_score,
        "raw": json.dumps({"creditReport": crb_data}),
        "metrics": json.dumps(crb_metrics.__dict__),
    })
    crb_report_id = crb_insert.fetchone()[0]
    await db.commit()

    # ── Fetch transactions for this customer ────────────────────────────────
    tx_rows = await db.execute(text("""
        SELECT transaction_date, amount, transaction_type, category,
               description, channel, balance_after
        FROM transactions WHERE customer_id = :cid
        ORDER BY transaction_date DESC LIMIT 500
    """), {"cid": customer_id})
    transactions = [dict(r._mapping) for r in tx_rows.fetchall()]

    # ── Compute hybrid score ─────────────────────────────────────────────────
    customer_name = f"{payload.customer.firstName} {payload.customer.lastName}"
    result = await compute_hybrid_score(
        customer_id=customer_id,
        customer_name=customer_name,
        transactions=transactions,
        crb_raw_report={"creditReport": crb_data},
    )

    # ── Persist score event ──────────────────────────────────────────────────
    event_row = await db.execute(text("""
        INSERT INTO credit_score_events
          (customer_id, base_score, crb_contribution, llm_adjustment,
           pd_probability, final_score, score_band, reasoning, crb_report_id,
           llm_provider, llm_model_name, model_target)
        VALUES (:cid, :base, :crb, :llm, :pd, :final, :band, :reasoning,
                :crb_rid, :llm_prov, :llm_mod, :target)
        RETURNING event_id
    """), {
        "cid": customer_id,
        "base": result.base_score,
        "crb": result.crb_contribution,
        "llm": result.llm_adjustment,
        "pd": result.pd_probability,
        "final": result.final_score,
        "band": result.score_band,
        "reasoning": "\n".join(result.reasoning),
        "crb_rid": crb_report_id,
        "llm_prov": result.llm_provider,
        "llm_mod": result.llm_model,
        "target": result.model_target,
    })
    event_id = event_row.scalar()

    # ── Persist base score breakdown ─────────────────────────────────────────
    br = result.base_result
    await db.execute(text("""
        INSERT INTO base_score_breakdowns
          (score_event_id, income_stability_score, avg_monthly_income,
           savings_rate_score, low_balance_score, transaction_diversity, base_total)
        VALUES (:eid, :inc_stab, :avg_inc, :sav_rate, :low_bal, :tx_div, :base_tot)
    """), {
        "eid": event_id,
        "inc_stab": br.income_stability_score,
        "avg_inc": br.avg_monthly_income,
        "sav_rate": br.savings_rate_score,
        "low_bal": br.low_balance_score,
        "tx_div": br.transaction_diversity_score,
        "base_tot": br.base_total,
    })
    await db.commit()

    elapsed = time.perf_counter() - start
    SCORING_REQUESTS.labels(model_target=result.model_target).inc()
    SCORING_LATENCY.observe(elapsed)
    logger.info("Score persisted", customer_id=customer_id, score=result.final_score, elapsed_s=elapsed)

    return ScoreResponse(
        customer_id=customer_id,
        base_score=result.base_score,
        crb_contribution=result.crb_contribution,
        llm_adjustment=result.llm_adjustment,
        pd_probability=result.pd_probability,
        final_score=result.final_score,
        score_band=result.score_band,
        reasoning=result.reasoning,
        llm_provider=result.llm_provider,
        llm_model=result.llm_model,
        scored_at=str(date.today()),
    )
