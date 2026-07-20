"""
Tests for ingestion/bank.py — SME bank-statement parsing, categorization and
row_hash dedupe keys.
"""
from datetime import datetime
from pathlib import Path

import pytest

from ingestion.bank import (
    CATEGORIES,
    PROJECTION_CATEGORY,
    StatementParseError,
    categorize,
    parse_csv,
    parse_statement,
    row_hash,
)

FIXTURES = Path(__file__).parent / "fixtures"

# KCB-style export: separate Debit/Credit columns, preamble, furniture row.
KCB_SAMPLE = (FIXTURES / "sample_bank_statement.csv").read_bytes()

# Equity-style export: Money Out/Money In columns, different header names.
EQUITY_SAMPLE = (
    "Date,Particulars,Money Out,Money In,Running Balance,Ref No\n"
    '2026-03-01,MPESA TILL SETTLEMENT 890123,,"80,000.00","95,000.00",EQ001\n'
    '2026-03-04,STANDING ORDER RENT,"20,000.00",,"75,000.00",EQ002\n'
    '2026-03-10,EXCISE DUTY,25.00,,"74,975.00",\n'
)

# NCBA-style export: single signed Amount column.
NCBA_SAMPLE = (
    "Txn Date,Narrative,Amount,Balance\n"
    '01-Apr-2026,CUSTOMER DEPOSIT POS SALES,"150,000.00","162,000.00"\n'
    '05-Apr-2026,PAYROLL RUN APRIL,"-45,000.00","117,000.00"\n'
    '20-Apr-2026,PESALINK TO SUPPLIER,"-12,000.00","105,000.00"\n'
)


class TestCsvParsing:
    def test_kcb_debit_credit_shape(self):
        stmt = parse_csv(KCB_SAMPLE)
        # 9 transaction rows; the OPENING BALANCE furniture row is skipped
        assert len(stmt.transactions) == 9
        assert stmt.source_format == "CSV"
        assert str(stmt.period_start) == "2026-02-01"
        assert str(stmt.period_end) == "2026-02-28"

    def test_kcb_direction_amount_balance_reference(self):
        stmt = parse_csv(KCB_SAMPLE)
        first = stmt.transactions[0]
        assert first.direction == "IN"
        assert first.amount == 120_000.00
        assert first.balance == 145_230.00
        assert first.reference == "FT26032ABC1"
        supplier = stmt.transactions[1]
        assert supplier.direction == "OUT"
        assert supplier.amount == 65_000.00
        ledger = next(t for t in stmt.transactions if "LEDGER" in t.details)
        assert ledger.reference is None

    def test_equity_money_out_in_shape(self):
        stmt = parse_csv(EQUITY_SAMPLE.encode())
        assert [t.direction for t in stmt.transactions] == ["IN", "OUT", "OUT"]
        assert stmt.transactions[0].amount == 80_000.00
        assert stmt.transactions[0].reference == "EQ001"
        assert stmt.transactions[1].balance == 75_000.00

    def test_ncba_signed_amount_shape(self):
        stmt = parse_csv(NCBA_SAMPLE.encode())
        assert [t.direction for t in stmt.transactions] == ["IN", "OUT", "OUT"]
        assert stmt.transactions[1].amount == 45_000.00
        assert stmt.transactions[0].txn_time == datetime(2026, 4, 1)

    def test_non_statement_rejected(self):
        with pytest.raises(StatementParseError):
            parse_csv(b"foo,bar\n1,2\n")

    def test_empty_file_rejected(self):
        with pytest.raises(StatementParseError):
            parse_statement(b"", "x.csv")

    def test_header_only_rejected(self):
        with pytest.raises(StatementParseError):
            parse_csv(b"Date,Description,Debit,Credit,Balance\n")

    def test_bad_date_fails_loud(self):
        data = b"Date,Description,Debit,Credit,Balance\nnot-a-date,SOMETHING,100.00,,900.00\n"
        with pytest.raises(StatementParseError):
            parse_csv(data)


class TestCategorizer:
    @pytest.mark.parametrize("details,direction,expected", [
        ("MPESA PAYBILL SETTLEMENT 522522", "IN", "SALES_INCOME"),
        ("CUSTOMER DEPOSIT POS SALES", "IN", "SALES_INCOME"),
        ("TILL SETTLEMENT 890123", "IN", "SALES_INCOME"),
        ("SUPPLIER PAYMENT - MABATI ROLLING MILLS INV 4471", "OUT", "SUPPLIER_PAYMENT"),
        ("STOCK PURCHASE LPO 221", "OUT", "SUPPLIER_PAYMENT"),
        ("STAFF SALARIES FEBRUARY", "OUT", "PAYROLL"),
        ("PAYROLL RUN APRIL", "OUT", "PAYROLL"),
        ("WAGES CASUAL WORKERS", "OUT", "PAYROLL"),
        ("NEMO WORKING CAPITAL LOAN DISBURSEMENT", "IN", "LOAN_DISBURSEMENT"),
        ("LOAN REPAYMENT NEMO WORKING CAPITAL", "OUT", "LOAN_REPAYMENT"),
        ("LEDGER FEE", "OUT", "BANK_CHARGES"),
        ("MONTHLY ACCOUNT MAINTENANCE CHARGE", "OUT", "BANK_CHARGES"),
        ("EXCISE DUTY", "OUT", "BANK_CHARGES"),
        ("KRA ITAX PAYE REMITTANCE", "OUT", "TAX"),
        ("VAT PAYMENT KRA", "OUT", "TAX"),
        ("KPLC ELECTRICITY BILL", "OUT", "UTILITY"),
        ("NAIROBI WATER BILL", "OUT", "UTILITY"),
        ("CASH DEPOSIT - BRANCH", "IN", "CASH_DEPOSIT"),
        ("ATM WITHDRAWAL KIMATHI ST", "OUT", "CASH_WITHDRAWAL"),
        ("CASH WITHDRAWAL COUNTER", "OUT", "CASH_WITHDRAWAL"),
        ("RTGS OUTWARD JENGA SUPPLIES", "OUT", "TRANSFER"),
        ("PESALINK FROM WANJIKU", "IN", "TRANSFER"),
        ("EFT INWARD", "IN", "TRANSFER"),
        ("MISC POSTING", "IN", "OTHER_IN"),
        ("MISC POSTING", "OUT", "OTHER_OUT"),
    ])
    def test_categories(self, details, direction, expected):
        assert categorize(details, direction) == expected

    def test_every_category_has_projection(self):
        assert set(CATEGORIES) == set(PROJECTION_CATEGORY.keys())
        # SME revenue must drive the income-stability scorecard dimension.
        assert PROJECTION_CATEGORY["SALES_INCOME"] == "SALARY"
        assert PROJECTION_CATEGORY["BANK_CHARGES"] == "CHARGES"

    def test_projection_targets_within_mpesa_vocabulary(self):
        from ingestion.mpesa import PROJECTION_CATEGORY as MPESA_PROJECTION
        assert set(PROJECTION_CATEGORY.values()) <= set(MPESA_PROJECTION.values())


class TestRowHash:
    def test_deterministic(self):
        t = datetime(2026, 2, 1, 0, 0, 0)
        h1 = row_hash(t, 120_000.00, "IN", 145_230.00, "MPESA PAYBILL SETTLEMENT 522522")
        h2 = row_hash(t, 120_000.00, "IN", 145_230.00, "MPESA  PAYBILL SETTLEMENT   522522")
        assert h1 == h2  # whitespace-normalized
        assert len(h1) == 64

    def test_distinct_rows_distinct_hashes(self):
        t = datetime(2026, 2, 1)
        base = row_hash(t, 100.00, "OUT", 900.00, "ATM WITHDRAWAL")
        assert row_hash(t, 100.00, "OUT", 800.00, "ATM WITHDRAWAL") != base  # balance differs
        assert row_hash(t, 100.00, "IN", 900.00, "ATM WITHDRAWAL") != base   # direction differs
        assert row_hash(t, 200.00, "OUT", 900.00, "ATM WITHDRAWAL") != base  # amount differs

    def test_reparse_yields_identical_hashes(self):
        first = [t.row_hash for t in parse_csv(KCB_SAMPLE).transactions]
        second = [t.row_hash for t in parse_csv(KCB_SAMPLE).transactions]
        assert first == second
        assert len(set(first)) == len(first)  # no collisions within the statement


class TestPdfDispatch:
    def test_pdf_magic_routes_to_pdf_parser(self):
        # Not a real PDF beyond magic bytes — must fail loudly, not fall through to CSV.
        with pytest.raises(StatementParseError):
            parse_statement(b"%PDF-1.7 garbage", "statement.pdf")

    def test_misnamed_pdf_rejected(self):
        with pytest.raises(StatementParseError):
            parse_statement(b"not,a,pdf", "statement.pdf")
