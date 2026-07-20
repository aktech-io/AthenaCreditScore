from __future__ import annotations

"""
DPA 2019 right-to-erasure flow (NemoScore Phase 5, contract 1.5.0):

  POST /api/v1/credit-score/{customer_id}/erasure

Erasure here means removing/pseudonymizing personal data while retaining what
Kenyan law and prudential practice require a lender's scoring engine to keep
(records of credit decisions). Concretely, in the scoring database:

  ERASED   customers PII columns (names → 'ERASED', identifiers/contacts/
           location → NULL; the numeric customer_id row survives as a
           tombstone so historic FKs stay intact)
  DELETED  raw statement data (mpesa_/bank_ statements + transactions,
           cascade), feature_values vectors, alert_preferences
  CLEARED  transactions.description/external_ref (amounts/dates retained,
           now unlinkable to a person), crb_reports.raw_report/
           extracted_metrics (bureau_score + date retained as decision
           provenance), credit_score_events.reasoning (may embed the name)
  RETAINED credit_score_events score/PD/reason-code columns and score_alerts
           (numeric decision records — DPA s.40(2) lawful-retention basis)

Out of scope for this endpoint (documented in docs/compliance/dpia.md):
customer-service's customers row lives in the same table (covered here),
media-service files and user-service accounts are erased via their own admin
APIs; the LMS holds its own loan records under its own retention schedule.

Access: ADMIN or SERVICE only — the right is exercised through the
DPO/support process, not self-service — and the body must echo the literal
confirmation string to make bulk accidents hard.
"""

import json
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


class ErasureRequest(BaseModel):
    confirm: str  # must be exactly "ERASE <customer_id>"


_ERASURE_STATEMENTS: Dict[str, str] = {
    # Raw consumer-permissioned statement data: delete outright.
    "mpesa_transactions": "DELETE FROM mpesa_transactions WHERE customer_id = :cid",
    "mpesa_statements": "DELETE FROM mpesa_statements WHERE customer_id = :cid",
    "bank_transactions": "DELETE FROM bank_transactions WHERE customer_id = :cid",
    "bank_statements": "DELETE FROM bank_statements WHERE customer_id = :cid",
    "feature_values": "DELETE FROM feature_values WHERE customer_id = :cid",
    "alert_preferences": "DELETE FROM alert_preferences WHERE customer_id = :cid",
    # Derived rows: strip free text that can identify the person.
    "transactions": """
        UPDATE transactions SET description = NULL, external_ref = NULL
        WHERE customer_id = :cid""",
    "crb_reports": """
        UPDATE crb_reports
        SET raw_report = '{}'::jsonb, extracted_metrics = '{}'::jsonb
        WHERE customer_id = :cid""",
    "credit_score_events": """
        UPDATE credit_score_events SET reasoning = NULL
        WHERE customer_id = :cid""",
    # The customer row becomes a tombstone.
    "customers": """
        UPDATE customers SET
            first_name = 'ERASED', last_name = 'ERASED', middle_name = NULL,
            national_id = NULL, mobile_number = NULL, email = NULL,
            date_of_birth = NULL, gender = NULL, region = NULL, county = NULL,
            sub_county = NULL, ward = NULL, latitude = NULL, longitude = NULL,
            id_type = NULL, id_expiry_date = NULL, bank_name = NULL,
            branch_name = NULL, account_number = NULL, mifos_client_id = NULL
        WHERE customer_id = :cid""",
}


@router.post("/credit-score/{customer_id}/erasure")
async def erase_customer_data(
    customer_id: int,
    body: ErasureRequest,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """DPA 2019 erasure of a customer's personal data from the scoring DB.
    Added in 1.5.0. Irreversible."""
    roles = claims.get("roles", [])
    if not any(r in roles for r in ("ADMIN", "SERVICE")):
        raise HTTPException(status_code=403, detail="Erasure requires ADMIN or SERVICE role")

    expected = f"ERASE {customer_id}"
    if body.confirm != expected:
        raise HTTPException(
            status_code=422,
            detail=f'Confirmation mismatch — body.confirm must be exactly "{expected}"',
        )

    exists = await db.execute(
        text("SELECT 1 FROM customers WHERE customer_id = :cid"), {"cid": customer_id}
    )
    if not exists.fetchone():
        raise HTTPException(status_code=404, detail="Customer not found")

    touched: Dict[str, int] = {}
    for table, stmt in _ERASURE_STATEMENTS.items():
        result = await db.execute(text(stmt), {"cid": customer_id})
        touched[table] = result.rowcount or 0

    requested_by = str(claims.get("sub") or claims.get("username") or "service")
    await db.execute(text("""
        INSERT INTO erasure_log (customer_id, requested_by, tables_touched)
        VALUES (:cid, :by, CAST(:touched AS jsonb))
    """), {"cid": customer_id, "by": requested_by, "touched": json.dumps(touched)})
    await db.commit()

    logger.info("Customer data erased", customer_id=customer_id,
                requested_by=requested_by, tables=touched)
    return {
        "customer_id": customer_id,
        "erased": True,
        "requested_by": requested_by,
        "tables_touched": touched,
        "retained": "credit_score_events score/PD/reason codes and score_alerts "
                    "(lawful retention of credit-decision records)",
    }
