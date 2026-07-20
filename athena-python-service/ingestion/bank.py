from __future__ import annotations

"""
Kenyan SME bank-statement parser + transaction categorizer (NemoScore Phase 2).

Parses consumer-permissioned bank statements — CSV export or (optionally
password-protected) PDF — from the common Kenyan banks (KCB, Equity, Co-op,
Absa, NCBA). Unlike M-Pesa there is no single canonical layout, so parsing is
driven by a normalized header map covering the export shapes seen in the wild:

    date:     Date / Txn Date / Transaction Date / Value Date / Posting Date
    details:  Description / Particulars / Details / Narrative / Narration
    money:    separate Debit/Credit (or Withdrawal/Deposit, Money Out/Money In)
              columns, OR a single signed Amount column
    balance:  Balance / Running Balance / Available Balance (optional)
    ref:      Reference / Ref No / Transaction Ref (optional)

Contract mirrors ingestion/mpesa.py: **fail loudly**. An undecodable file, an
unrecognized layout, or a statement with zero transactions raises
StatementParseError — never a silently-empty result. Non-transaction furniture
rows (opening/closing balance, B/F, totals, page footers) are skipped; any
other row that fails to parse aborts the ingest.

Banks have no universal receipt number, so per-row dedupe uses a deterministic
`row_hash` = sha256 of (normalized date | amount | direction | balance |
details) — stable across re-exports of the same period, and collision-safe in
practice because two genuinely distinct same-day transactions differ in
balance or details.

Categories are the SME ML vocabulary (stored on bank_transactions and consumed
by features/pipeline.py v3). PROJECTION_CATEGORY maps them to the coarser
`transactions.category` vocabulary the base scorecard reads — the same target
set the M-Pesa projection uses.
"""

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import structlog

from ingestion.mpesa import StatementParseError  # shared fail-loud contract

logger = structlog.get_logger(__name__)


@dataclass
class ParsedTransaction:
    row_hash: str          # sha256 dedupe key, see module docstring
    txn_time: datetime
    details: str
    category: str          # SME ML vocabulary, see CATEGORIES
    direction: str         # IN | OUT
    amount: float          # always positive
    balance: Optional[float]
    reference: Optional[str]


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
    "SALES_INCOME", "SUPPLIER_PAYMENT", "PAYROLL",
    "LOAN_DISBURSEMENT", "LOAN_REPAYMENT", "BANK_CHARGES", "TAX",
    "UTILITY", "CASH_DEPOSIT", "CASH_WITHDRAWAL", "TRANSFER",
    "OTHER_IN", "OTHER_OUT",
]

# Maps SME categories → the coarser transactions.category vocabulary consumed
# by the base scorecard (same target set as ingestion/mpesa.py). SALES_INCOME
# projects to SALARY deliberately: recurring business revenue is the SME's
# income and must drive the income-stability scorecard dimension.
PROJECTION_CATEGORY = {
    "SALES_INCOME": "SALARY",
    "SUPPLIER_PAYMENT": "SHOPPING",
    "PAYROLL": "BILLS",
    "LOAN_DISBURSEMENT": "LOAN",
    "LOAN_REPAYMENT": "LOAN_REPAYMENT",
    "BANK_CHARGES": "CHARGES",
    "TAX": "BILLS",
    "UTILITY": "UTILITY",
    "CASH_DEPOSIT": "CASH_DEPOSIT",
    "CASH_WITHDRAWAL": "CASH_WITHDRAWAL",
    "TRANSFER": "TRANSFER",
    "OTHER_IN": "OTHER",
    "OTHER_OUT": "OTHER",
}

_CHARGES = re.compile(
    r"\bcharges?\b|\bfees?\b|commission|excise|ledger fee|account maintenance",
    re.I,
)
_TAX = re.compile(
    r"\bkra\b|i-?tax|\bpaye\b|\bvat\b|withholding tax|advance tax|turnover tax|tax payment",
    re.I,
)
_PAYROLL = re.compile(r"salar(?:y|ies)|\bwages\b|payroll|staff payment", re.I)
_LOAN = re.compile(r"\bloan\b|facility (?:repayment|disbursement)", re.I)
_CASH_DEPOSIT = re.compile(r"cash deposit|\bcash dep\b|cdm deposit", re.I)
_CASH_WITHDRAWAL = re.compile(r"cash withdrawal|\batm\b|cheque withdrawal|\bwdl\b", re.I)
_SALES = re.compile(
    r"m-?pesa|pay ?bill|\btill\b|\bpos\b|\bsales\b|customer (?:payment|deposit)|till settlement",
    re.I,
)
_SUPPLIER = re.compile(r"supplier|purchase|\binv(?:oice)?\b|\blpo\b|\bstock\b", re.I)
_UTILITY = re.compile(
    r"kplc|kenya power|electricity|water|dstv|gotv|zuku|startimes|internet|wifi|rent\b",
    re.I,
)
_TRANSFER = re.compile(r"transfer|\btrf\b|\brtgs\b|\beft\b|pesalink|standing order", re.I)


def categorize(details: str, direction: str) -> str:
    """Classify one narrative string into the SME category vocabulary."""
    low = " ".join(details.split()).lower()

    if _CHARGES.search(low):
        return "BANK_CHARGES"
    if direction == "OUT" and _TAX.search(low):
        return "TAX"
    if direction == "OUT" and _PAYROLL.search(low):
        return "PAYROLL"
    if _LOAN.search(low):
        return "LOAN_REPAYMENT" if direction == "OUT" else "LOAN_DISBURSEMENT"
    if direction == "IN" and _CASH_DEPOSIT.search(low):
        return "CASH_DEPOSIT"
    if direction == "OUT" and _CASH_WITHDRAWAL.search(low):
        return "CASH_WITHDRAWAL"
    if direction == "IN" and _SALES.search(low):
        return "SALES_INCOME"
    if direction == "OUT" and _SUPPLIER.search(low):
        return "SUPPLIER_PAYMENT"
    if direction == "OUT" and _UTILITY.search(low):
        return "UTILITY"
    if _TRANSFER.search(low):
        return "TRANSFER"
    return "OTHER_IN" if direction == "IN" else "OTHER_OUT"


# ── Parsing helpers ─────────────────────────────────────────────────────────

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %b %Y",
)


def _parse_time(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise StatementParseError(f"Unrecognized transaction date: {raw!r}")


def _parse_money(raw: Optional[str]) -> float:
    """'1,234.56' / '-1,234.56' / '(1,234.56)' / '1,234.56 CR' / '' → float."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", "").replace("KSh", "").replace("Ksh", "").replace("KES", "").strip()
    if not s or s in ("-", "–"):
        return 0.0
    # Some exports suffix DR/CR on balances; DR means overdrawn (negative).
    suffix = None
    m = re.search(r"\s*(DR|CR)$", s, re.I)
    if m:
        suffix = m.group(1).upper()
        s = s[: m.start()].strip()
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        value = float(s)
    except ValueError:
        raise StatementParseError(f"Unparseable amount: {raw!r}")
    if negative or suffix == "DR":
        value = -abs(value)
    return value


def _norm_header(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


# Normalized header → canonical field. Covers CSV exports and PDF table
# headers across KCB / Equity / Co-op / Absa / NCBA shapes. First match wins
# (e.g. Transaction Date preferred over a later Value Date column).
_HEADER_MAP = {
    "date": "date",
    "txndate": "date",
    "trandate": "date",
    "transactiondate": "date",
    "valuedate": "date",
    "postingdate": "date",
    "description": "details",
    "particulars": "details",
    "details": "details",
    "narrative": "details",
    "narration": "details",
    "transactiondetails": "details",
    "transactionremarks": "details",
    "debit": "debit",
    "debits": "debit",
    "debitamount": "debit",
    "withdrawal": "debit",
    "withdrawals": "debit",
    "withdrawalamount": "debit",
    "moneyout": "debit",
    "paidout": "debit",
    "credit": "credit",
    "credits": "credit",
    "creditamount": "credit",
    "deposit": "credit",
    "deposits": "credit",
    "depositamount": "credit",
    "moneyin": "credit",
    "paidin": "credit",
    "amount": "amount",           # single signed Amount column variant
    "transactionamount": "amount",
    "txnamount": "amount",
    "balance": "balance",
    "runningbalance": "balance",
    "availablebalance": "balance",
    "closingbalance": "balance",
    "bookbalance": "balance",
    "reference": "reference",
    "ref": "reference",
    "refno": "reference",
    "referenceno": "reference",
    "transactionref": "reference",
    "transactionreference": "reference",
    "transactionid": "reference",
}

# Non-transaction furniture rows banks embed in the table — skipped, not fatal.
_FURNITURE = re.compile(
    r"opening balance|closing balance|balance (?:b/?f|c/?f)|\bb/f\b|\bc/f\b|"
    r"brought forward|carried forward|^totals?\b|page \d+",
    re.I,
)


def _is_header_row(cells: List[str]) -> bool:
    canon = {_HEADER_MAP.get(_norm_header(c or "")) for c in cells}
    return "date" in canon and "details" in canon


def row_hash(
    txn_time: datetime, amount: float, direction: str,
    balance: Optional[float], details: str,
) -> str:
    """Deterministic per-row dedupe key — banks lack universal receipt numbers."""
    key = "|".join([
        txn_time.strftime("%Y-%m-%dT%H:%M:%S"),
        f"{amount:.2f}",
        direction,
        "" if balance is None else f"{balance:.2f}",
        " ".join(details.split()).upper(),
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _rows_to_transactions(header: List[str], rows: List[List[str]]) -> List[ParsedTransaction]:
    cols = {}
    for idx, h in enumerate(header):
        canon = _HEADER_MAP.get(_norm_header(h or ""))
        if canon and canon not in cols:
            cols[canon] = idx

    if not {"date", "details"}.issubset(cols) or not ({"debit", "credit", "amount"} & cols.keys()):
        raise StatementParseError(
            "Not a recognized bank statement: expected a Date and Description/"
            "Particulars column plus Debit/Credit (or Amount) columns."
        )

    def cell(row: List[str], key: str) -> Optional[str]:
        i = cols.get(key)
        return row[i] if i is not None and i < len(row) else None

    txns: List[ParsedTransaction] = []
    for row in rows:
        if not any((c or "").strip() for c in row):
            continue  # blank line
        if _is_header_row([(c or "") for c in row]):
            continue  # repeated page headers
        date_raw = (cell(row, "date") or "").strip()
        details = " ".join((cell(row, "details") or "").split())
        if _FURNITURE.search(details) or _FURNITURE.search(date_raw):
            continue  # opening/closing balance, B/F, totals, page footers
        if not date_raw:
            raise StatementParseError(f"Transaction row has no date: {details[:80]!r}")

        if "debit" in cols or "credit" in cols:
            debit = abs(_parse_money(cell(row, "debit")))
            credit = abs(_parse_money(cell(row, "credit")))
            if credit > 0:
                direction, amount = "IN", credit
            elif debit > 0:
                direction, amount = "OUT", debit
            else:
                continue  # zero-value row
        else:
            signed = _parse_money(cell(row, "amount"))
            if signed == 0:
                continue
            direction = "IN" if signed > 0 else "OUT"
            amount = abs(signed)

        txn_time = _parse_time(date_raw)
        balance_raw = cell(row, "balance")
        balance = _parse_money(balance_raw) if balance_raw not in (None, "") else None
        reference = (cell(row, "reference") or "").strip()[:100] or None
        amount = round(amount, 2)
        txns.append(ParsedTransaction(
            row_hash=row_hash(txn_time, amount, direction, balance, details),
            txn_time=txn_time,
            details=details,
            category=categorize(details, direction),
            direction=direction,
            amount=amount,
            balance=balance,
            reference=reference,
        ))
    return txns


# ── Entry points ────────────────────────────────────────────────────────────

def parse_csv(data: bytes) -> ParsedStatement:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    # Exports commonly carry preamble lines (account holder, account number,
    # statement period) before the table — find the header row.
    reader = list(csv.reader(io.StringIO(text)))
    header_idx = next((i for i, row in enumerate(reader) if _is_header_row(row)), None)
    if header_idx is None:
        raise StatementParseError(
            "No transaction header row found — is this a bank statement CSV?"
        )

    txns = _rows_to_transactions(reader[header_idx], reader[header_idx + 1:])
    if not txns:
        raise StatementParseError("Statement contains no transactions.")
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
                "PDF is password-protected — supply the statement password."
            ) from exc
        raise StatementParseError("Could not open PDF file.") from exc

    header: Optional[List[str]] = None
    rows: List[List[str]] = []
    with pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    cells = [(c or "").strip() for c in row]
                    if _is_header_row(cells):
                        header = cells
                    elif header:
                        rows.append(cells)

    if header is None:
        raise StatementParseError(
            "No transaction table found in PDF — is this a bank statement?"
        )
    txns = _rows_to_transactions(header, rows)
    if not txns:
        raise StatementParseError("Statement contains no transactions.")
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
