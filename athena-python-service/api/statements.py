from __future__ import annotations

"""
Consumer-permissioned M-Pesa statement upload (NemoScore Phase 2).

POST /api/v1/credit-score/statements/mpesa
  multipart: file (CSV or PDF), customer_id, optional pdf_password

Flow: parse → dedupe (whole file by sha256, per-row by receipt number) →
persist mpesa_statements/mpesa_transactions → project new rows into the
generic `transactions` table (channel MPESA) so the base scorecard sees the
same data → recompute the customer's lgbm_features vector.

Auth: customers may upload their own statement only; ADMIN/ANALYST/SERVICE
may upload for any customer. X-Tenant-Id honored as elsewhere.
"""

import hashlib
from collections import Counter
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db
from ingestion.mpesa import PROJECTION_CATEGORY, StatementParseError, parse_statement

logger = structlog.get_logger(__name__)
router = APIRouter()

MAX_STATEMENT_BYTES = 10 * 1024 * 1024  # generous: multi-year PDFs are ~2 MB


class StatementUploadResponse(BaseModel):
    statement_id: int
    customer_id: int
    source_format: str
    period_start: Optional[str]
    period_end: Optional[str]
    transactions_ingested: int
    duplicates_skipped: int
    category_totals: Dict[str, float]
    features_recomputed: bool


def _check_upload_access(claims: dict, customer_id: int) -> None:
    roles: List[str] = claims.get("roles", [])
    if any(r in roles for r in ("ADMIN", "ANALYST", "SERVICE")):
        return
    if str(claims.get("customerId")) != str(customer_id):
        raise HTTPException(status_code=403, detail="You may only upload your own statement")


@router.post("/credit-score/statements/mpesa", response_model=StatementUploadResponse)
async def upload_mpesa_statement(
    file: UploadFile = File(...),
    customer_id: int = Form(...),
    pdf_password: Optional[str] = Form(None),
    x_tenant_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    _check_upload_access(claims, customer_id)
    tenant_id = (x_tenant_id or "nemo").strip() or "nemo"

    data = await file.read()
    if len(data) > MAX_STATEMENT_BYTES:
        raise HTTPException(status_code=413, detail="Statement file too large (max 10 MB)")

    cust = await db.execute(
        text("SELECT 1 FROM customers WHERE customer_id = :cid"), {"cid": customer_id}
    )
    if not cust.fetchone():
        raise HTTPException(status_code=404, detail="Customer not found")

    file_sha256 = hashlib.sha256(data).hexdigest()
    dup = await db.execute(text("""
        SELECT statement_id FROM mpesa_statements
        WHERE customer_id = :cid AND file_sha256 = :sha
    """), {"cid": customer_id, "sha": file_sha256})
    existing = dup.fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"This exact file was already ingested (statement_id={existing[0]})",
        )

    try:
        parsed = parse_statement(data, filename=file.filename or "", password=pdf_password)
    except StatementParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    stmt_row = await db.execute(text("""
        INSERT INTO mpesa_statements
            (customer_id, source_format, file_sha256, period_start, period_end, tenant_id)
        VALUES (:cid, :fmt, :sha, :pstart, :pend, :tenant)
        RETURNING statement_id
    """), {
        "cid": customer_id, "fmt": parsed.source_format, "sha": file_sha256,
        "pstart": parsed.period_start, "pend": parsed.period_end, "tenant": tenant_id,
    })
    statement_id = stmt_row.fetchone()[0]

    ingested = 0
    duplicates = 0
    category_totals: Counter = Counter()
    for t in parsed.transactions:
        row = await db.execute(text("""
            INSERT INTO mpesa_transactions
                (statement_id, customer_id, receipt_no, txn_time, details,
                 category, direction, amount, balance, counterparty, tenant_id)
            VALUES (:sid, :cid, :receipt, :time, :details,
                    :cat, :dir, :amount, :balance, :cparty, :tenant)
            ON CONFLICT (customer_id, receipt_no) DO NOTHING
            RETURNING txn_id
        """), {
            "sid": statement_id, "cid": customer_id, "receipt": t.receipt_no,
            "time": t.txn_time, "details": t.details, "cat": t.category,
            "dir": t.direction, "amount": t.amount, "balance": t.balance,
            "cparty": t.counterparty, "tenant": tenant_id,
        })
        if row.fetchone() is None:
            duplicates += 1  # receipt already ingested via an overlapping statement
            continue
        ingested += 1
        category_totals[t.category] += t.amount

        # Projection: the base scorecard reads `transactions`. Receipt-level
        # dedupe above guarantees we never project the same row twice.
        await db.execute(text("""
            INSERT INTO transactions
                (customer_id, transaction_date, amount, transaction_type,
                 category, description, channel, balance_after, external_ref)
            VALUES (:cid, :date, :amount, :type, :cat, :desc, 'MPESA', :balance, :ref)
        """), {
            "cid": customer_id, "date": t.txn_time.date(), "amount": t.amount,
            "type": "CREDIT" if t.direction == "IN" else "DEBIT",
            "cat": PROJECTION_CATEGORY.get(t.category, "OTHER"),
            "desc": t.details[:500], "balance": t.balance,
            "ref": f"MPESA:{t.receipt_no}",
        })

    await db.execute(text("""
        UPDATE mpesa_statements
        SET n_transactions = :n, n_duplicates = :d
        WHERE statement_id = :sid
    """), {"n": ingested, "d": duplicates, "sid": statement_id})
    await db.commit()

    features_recomputed = False
    try:
        from features.pipeline import compute_and_store_features
        features_recomputed = await compute_and_store_features(db, customer_id) is not None
    except Exception as exc:
        # Feature refresh is best-effort here; the vector is also recomputed
        # on the next scoring miss. The ingest itself has already committed.
        logger.warning("Feature recompute after ingest failed", customer_id=customer_id, error=str(exc))

    logger.info(
        "M-Pesa statement ingested",
        customer_id=customer_id, statement_id=statement_id,
        ingested=ingested, duplicates=duplicates, fmt=parsed.source_format,
    )
    return StatementUploadResponse(
        statement_id=statement_id,
        customer_id=customer_id,
        source_format=parsed.source_format,
        period_start=str(parsed.period_start) if parsed.period_start else None,
        period_end=str(parsed.period_end) if parsed.period_end else None,
        transactions_ingested=ingested,
        duplicates_skipped=duplicates,
        category_totals={k: round(v, 2) for k, v in category_totals.most_common()},
        features_recomputed=features_recomputed,
    )
