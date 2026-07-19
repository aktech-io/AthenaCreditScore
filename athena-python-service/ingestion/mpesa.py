from __future__ import annotations

"""
M-Pesa statement parser + transaction categorizer (NemoScore Phase 2).

Parses consumer-permissioned Safaricom M-Pesa full statements — CSV export or
the password-protected PDF — into normalized transactions:

    Receipt No. | Completion Time | Details | Transaction Status | Paid In | Withdrawn | Balance

Contract mirrors the rest of NemoScore: **fail loudly**. An undecodable file,
an unrecognized layout, or a statement with zero completed transactions raises
StatementParseError — never a silently-empty result.

Categories are the ML vocabulary (stored on mpesa_transactions and consumed by
features/pipeline.py v2). PROJECTION_CATEGORY maps them to the coarser
`transactions.category` vocabulary the base scorecard reads (SALARY, BETTING,
UTILITY drive scorecard dimensions — see scoring/base_scorer.py).
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class StatementParseError(ValueError):
    """Raised when a statement file cannot be parsed. Message is user-safe."""


@dataclass
class ParsedTransaction:
    receipt_no: str
    txn_time: datetime
    details: str
    category: str          # ML vocabulary, see CATEGORIES
    direction: str         # IN | OUT
    amount: float          # always positive
    balance: Optional[float]
    counterparty: Optional[str]


@dataclass
class ParsedStatement:
    source_format: str     # CSV | PDF
    transactions: List[ParsedTransaction] = field(default_factory=list)

    @property
    def period_start(self):
        return min(t.txn_time for t in self.transactions).date() if self.transactions else None

    @property
    def period_end(self):
        return max(t.txn_time for t in self.transactions).date() if self.transactions else None


# ── Categorization ──────────────────────────────────────────────────────────

CATEGORIES = [
    "SALARY", "RECEIVED", "SENT", "PAYBILL", "MERCHANT", "UTILITY", "AIRTIME",
    "WITHDRAWAL", "DEPOSIT", "SAVINGS_DEPOSIT", "SAVINGS_WITHDRAWAL",
    "LOAN_DISBURSEMENT", "LOAN_REPAYMENT", "FULIZA_DRAW", "FULIZA_REPAY",
    "BETTING", "CHARGES", "OTHER",
]

# Maps ML categories → the coarser transactions.category vocabulary consumed
# by the base scorecard (diversity counts distinct debit categories; SALARY
# and BETTING labels feed pattern detection).
PROJECTION_CATEGORY = {
    "SALARY": "SALARY",
    "RECEIVED": "TRANSFER_IN",
    "SENT": "TRANSFER",
    "PAYBILL": "BILLS",
    "MERCHANT": "SHOPPING",
    "UTILITY": "UTILITY",
    "AIRTIME": "AIRTIME",
    "WITHDRAWAL": "CASH_WITHDRAWAL",
    "DEPOSIT": "CASH_DEPOSIT",
    "SAVINGS_DEPOSIT": "SAVINGS",
    "SAVINGS_WITHDRAWAL": "SAVINGS",
    "LOAN_DISBURSEMENT": "LOAN",
    "LOAN_REPAYMENT": "LOAN_REPAYMENT",
    "FULIZA_DRAW": "LOAN",
    "FULIZA_REPAY": "LOAN_REPAYMENT",
    "BETTING": "BETTING",
    "CHARGES": "CHARGES",
    "OTHER": "OTHER",
}

_BETTING_NAMES = re.compile(
    r"sportpesa|betika|odibets|betway|1xbet|22bet|mozzart|sportybet|melbet|betlion|shabiki|mcheza",
    re.I,
)
_UTILITY_NAMES = re.compile(
    r"kplc|kenya power|nairobi water|nairobi city water|dstv|gotv|zuku|startimes|"
    r"safaricom home|water and sewerage|multichoice",
    re.I,
)

# "... from 254708374149 - JANE WAMBUI", "... to 888880 - KPLC PREPAID Acc. 123"
_COUNTERPARTY = re.compile(
    r"(?:from|to|at(?:\s+agent)?(?:\s+till)?)\s+"
    r"(?:[0-9*]{4,}\s*[-–]\s*)?(?P<name>[^.]{2,})",
    re.I,
)


def categorize(details: str, direction: str) -> Tuple[str, Optional[str]]:
    """Classify one Details string. Returns (category, counterparty)."""
    d = " ".join(details.split())  # collapse PDF cell newlines
    low = d.lower()

    m = _COUNTERPARTY.search(d)
    counterparty = m.group("name").strip().rstrip("-–— ") if m else None
    if counterparty:
        # Trim account suffixes: "KPLC PREPAID Acc 123", "Betika K Acc. 254708..."
        counterparty = re.split(r"\s+acc\b", counterparty, flags=re.I)[0].strip()[:200]

    def done(cat: str) -> Tuple[str, Optional[str]]:
        return cat, counterparty

    if "charge" in low or "fee" in low:
        return done("CHARGES")
    if "fuliza" in low or low.startswith("od ") or "overdraft" in low or "od loan" in low:
        return done("FULIZA_REPAY" if direction == "OUT" else "FULIZA_DRAW")
    if "m-shwari" in low or "mshwari" in low or "kcb m-pesa" in low:
        if "loan" in low:
            return done("LOAN_REPAYMENT" if direction == "OUT" else "LOAN_DISBURSEMENT")
        return done("SAVINGS_DEPOSIT" if direction == "OUT" else "SAVINGS_WITHDRAWAL")
    if _BETTING_NAMES.search(low):
        return done("BETTING")
    if "airtime" in low or "bundles" in low:
        return done("AIRTIME")
    if "salary" in low and direction == "IN":
        return done("SALARY")
    if "pay bill" in low or "paybill" in low:
        return done("UTILITY" if _UTILITY_NAMES.search(low) else "PAYBILL")
    if "merchant payment" in low or "buy goods" in low:
        return done("MERCHANT")
    if "withdrawal" in low and "agent" in low:
        return done("WITHDRAWAL")
    if "deposit of funds" in low or ("deposit" in low and "agent" in low):
        return done("DEPOSIT")
    if direction == "IN" and ("funds received" in low or "received from" in low
                              or "business payment" in low or "promotion payment" in low):
        return done("RECEIVED")
    if direction == "OUT" and ("transfer of funds" in low or "transfer to" in low
                               or "send money" in low):
        return done("SENT")
    return done("OTHER")


# ── Parsing helpers ─────────────────────────────────────────────────────────

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
)


def _parse_time(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise StatementParseError(f"Unrecognized transaction timestamp: {raw!r}")


def _parse_money(raw: Optional[str]) -> float:
    """'1,234.56' / '-1,234.56' / '(1,234.56)' / '' → float."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", "").replace("KSh", "").replace("Ksh", "").strip()
    if not s or s in ("-", "–"):
        return 0.0
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        value = float(s)
    except ValueError:
        raise StatementParseError(f"Unparseable amount: {raw!r}")
    return -value if negative else value


def _norm_header(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


# Normalized header → canonical field. Covers CSV export and PDF table headers.
_HEADER_MAP = {
    "receiptno": "receipt",
    "receipt": "receipt",
    "completiontime": "time",
    "completedtime": "time",
    "details": "details",
    "transactiondetails": "details",
    "transactionstatus": "status",
    "status": "status",
    "paidin": "paid_in",
    "withdrawn": "withdrawn",
    "withdraw": "withdrawn",
    "amount": "amount",           # some exports: single signed Amount column
    "balance": "balance",
}


def _rows_to_transactions(header: List[str], rows: List[List[str]]) -> List[ParsedTransaction]:
    cols = {}
    for idx, h in enumerate(header):
        canon = _HEADER_MAP.get(_norm_header(h or ""))
        if canon and canon not in cols:
            cols[canon] = idx

    required = {"receipt", "time", "details"}
    if not required.issubset(cols) or not ({"paid_in", "withdrawn", "amount"} & cols.keys()):
        raise StatementParseError(
            "Not an M-Pesa statement: expected columns Receipt No., Completion Time, "
            "Details and Paid In/Withdrawn (or Amount)."
        )

    def cell(row: List[str], key: str) -> Optional[str]:
        i = cols.get(key)
        return row[i] if i is not None and i < len(row) else None

    txns: List[ParsedTransaction] = []
    for row in rows:
        receipt = (cell(row, "receipt") or "").strip()
        if not receipt or _norm_header(receipt) == "receiptno":  # repeated page headers
            continue
        status = (cell(row, "status") or "Completed").strip().lower()
        if status and status != "completed":
            continue

        if "amount" in cols and "paid_in" not in cols:
            signed = _parse_money(cell(row, "amount"))
            direction = "IN" if signed >= 0 else "OUT"
            amount = abs(signed)
        else:
            paid_in = _parse_money(cell(row, "paid_in"))
            withdrawn = abs(_parse_money(cell(row, "withdrawn")))
            if paid_in > 0:
                direction, amount = "IN", paid_in
            elif withdrawn > 0:
                direction, amount = "OUT", withdrawn
            else:
                continue  # zero-value row (e.g. failed reversal remnants)

        details = " ".join((cell(row, "details") or "").split())
        balance_raw = cell(row, "balance")
        balance = _parse_money(balance_raw) if balance_raw not in (None, "") else None
        category, counterparty = categorize(details, direction)
        txns.append(ParsedTransaction(
            receipt_no=receipt[:20],
            txn_time=_parse_time(cell(row, "time") or ""),
            details=details,
            category=category,
            direction=direction,
            amount=round(amount, 2),
            balance=balance,
            counterparty=counterparty,
        ))
    return txns


# ── Entry points ────────────────────────────────────────────────────────────

def parse_csv(data: bytes) -> ParsedStatement:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    # The CSV export sometimes carries preamble lines (customer name, MSISDN,
    # period) before the table — find the header row.
    reader = list(csv.reader(io.StringIO(text)))
    header_idx = next(
        (i for i, row in enumerate(reader)
         if any(_norm_header(c) in ("receiptno", "receipt") for c in row)),
        None,
    )
    if header_idx is None:
        raise StatementParseError("No 'Receipt No.' header found — is this an M-Pesa statement CSV?")

    txns = _rows_to_transactions(reader[header_idx], reader[header_idx + 1:])
    if not txns:
        raise StatementParseError("Statement contains no completed transactions.")
    return ParsedStatement(source_format="CSV", transactions=txns)


def parse_pdf(data: bytes, password: Optional[str] = None) -> ParsedStatement:
    try:
        import pdfplumber
    except ImportError as exc:  # dependency is in requirements.txt; keep loud
        raise StatementParseError("PDF parsing unavailable: pdfplumber not installed.") from exc

    try:
        pdf = pdfplumber.open(io.BytesIO(data), password=password or "")
    except Exception as exc:
        msg = str(exc).lower()
        if "password" in msg or "decrypt" in msg or "encrypted" in msg:
            raise StatementParseError(
                "PDF is password-protected — supply the statement password "
                "(usually your national ID number)."
            ) from exc
        raise StatementParseError("Could not open PDF file.") from exc

    header: Optional[List[str]] = None
    rows: List[List[str]] = []
    with pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    cells = [(c or "").strip() for c in row]
                    if any(_norm_header(c) in ("receiptno", "receipt") for c in cells):
                        header = cells
                    elif header:
                        rows.append(cells)

    if header is None:
        raise StatementParseError(
            "No transaction table found in PDF — is this an M-Pesa full statement?"
        )
    txns = _rows_to_transactions(header, rows)
    if not txns:
        raise StatementParseError("Statement contains no completed transactions.")
    return ParsedStatement(source_format="PDF", transactions=txns)


def parse_statement(
    data: bytes, filename: str = "", password: Optional[str] = None
) -> ParsedStatement:
    """Dispatch on content (magic bytes) first, filename second."""
    if not data:
        raise StatementParseError("Empty file.")
    if data[:5] == b"%PDF-":
        return parse_pdf(data, password)
    if filename.lower().endswith(".pdf"):
        raise StatementParseError("File has a .pdf name but is not a valid PDF.")
    return parse_csv(data)
