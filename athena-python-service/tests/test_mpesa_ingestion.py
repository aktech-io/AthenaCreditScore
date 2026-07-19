"""
Tests for ingestion/mpesa.py — statement parsing and transaction categorization.
"""
import pytest

from ingestion.mpesa import (
    PROJECTION_CATEGORY,
    StatementParseError,
    categorize,
    parse_csv,
    parse_statement,
)

HEADER = "Receipt No.,Completion Time,Details,Transaction Status,Paid In,Withdrawn,Balance\n"


def make_csv(*rows: str) -> bytes:
    return (HEADER + "\n".join(rows)).encode()


SAMPLE = make_csv(
    'SFA1AAAA01,2026-05-02 09:15:00,Business Payment from 123456 - ACME LTD Salary Payment,Completed,"52,000.00",,52340.00',
    'SFA1AAAA02,2026-05-02 10:01:11,Customer Transfer of Funds Charge,Completed,,7.00,52333.00',
    'SFA1AAAA03,2026-05-03 12:30:00,Pay Bill to 888880 - KPLC PREPAID Acc. 1234,Completed,,"1,500.00",50833.00',
    'SFA1AAAA04,2026-05-04 18:45:10,Merchant Payment to 567890 - NAIVAS SUPERMARKET,Completed,,"3,200.00",47633.00',
    'SFA1AAAA05,2026-05-05 08:00:00,Customer Airtime Purchase,Completed,,100.00,47533.00',
    'SFA1AAAA06,2026-05-06 20:12:00,Pay Bill to 290290 - BETIKA Acc. 254708,Completed,,500.00,47033.00',
    'SFA1AAAA07,2026-05-07 07:00:00,M-Shwari Deposit,Completed,,"10,000.00",37033.00',
    'SFA1AAAA08,2026-05-08 13:00:00,OD Loan Repayment to 232323 - Fuliza M-PESA,Completed,,850.00,36183.00',
    'SFA1AAAA09,2026-05-09 16:20:00,Customer Withdrawal at Agent Till 98765 - JOYCE SHOP,Completed,,"5,000.00",31183.00',
    'SFA1AAAA10,2026-05-10 11:00:00,Funds received from 254708374149 - JANE WAMBUI,Completed,"2,000.00",,33183.00',
    'SFA1AAAA11,2026-05-11 11:00:00,Customer Transfer of Funds to 254711000000 - PETER K,Failed,,900.00,33183.00',
)


class TestCsvParsing:
    def test_parses_completed_rows_only(self):
        stmt = parse_csv(SAMPLE)
        assert len(stmt.transactions) == 10  # the Failed row is skipped
        assert stmt.source_format == "CSV"

    def test_period_from_transactions(self):
        stmt = parse_csv(SAMPLE)
        assert str(stmt.period_start) == "2026-05-02"
        assert str(stmt.period_end) == "2026-05-10"

    def test_direction_and_amounts(self):
        stmt = parse_csv(SAMPLE)
        first = stmt.transactions[0]
        assert first.direction == "IN"
        assert first.amount == 52000.00
        assert first.balance == 52340.00
        kplc = next(t for t in stmt.transactions if t.receipt_no == "SFA1AAAA03")
        assert kplc.direction == "OUT"
        assert kplc.amount == 1500.00

    def test_preamble_lines_before_header_ok(self):
        data = b"MPESA STATEMENT\nCustomer Name: JANE DOE\n\n" + SAMPLE
        stmt = parse_csv(data)
        assert len(stmt.transactions) == 10

    def test_non_statement_rejected(self):
        with pytest.raises(StatementParseError):
            parse_csv(b"foo,bar\n1,2\n")

    def test_empty_file_rejected(self):
        with pytest.raises(StatementParseError):
            parse_statement(b"", "x.csv")

    def test_signed_amount_column_variant(self):
        data = (
            "Receipt No.,Completion Time,Details,Amount,Balance\n"
            'SFB1BBBB01,2026-05-01 10:00:00,Funds received from 254700000001 - A B,"1,000.00",1000.00\n'
            'SFB1BBBB02,2026-05-02 10:00:00,Customer Transfer of Funds to 254700000002 - C D,"-400.00",600.00\n'
        ).encode()
        stmt = parse_csv(data)
        assert [t.direction for t in stmt.transactions] == ["IN", "OUT"]
        assert stmt.transactions[1].amount == 400.00


class TestCategorizer:
    @pytest.mark.parametrize("details,direction,expected", [
        ("Business Payment from 123456 - ACME LTD Salary Payment", "IN", "SALARY"),
        ("Funds received from 254708374149 - JANE WAMBUI", "IN", "RECEIVED"),
        ("Customer Transfer of Funds to 254711 - PETER K", "OUT", "SENT"),
        ("Pay Bill to 888880 - KPLC PREPAID Acc. 1234", "OUT", "UTILITY"),
        ("Pay Bill to 400200 - EQUITY PAYBILL Acc. 99", "OUT", "PAYBILL"),
        ("Pay Bill to 290290 - BETIKA Acc. 254708", "OUT", "BETTING"),
        ("Pay Bill to 955100 - SPORTPESA", "OUT", "BETTING"),
        ("Merchant Payment to 567890 - NAIVAS SUPERMARKET", "OUT", "MERCHANT"),
        ("Customer Airtime Purchase", "OUT", "AIRTIME"),
        ("Buy Bundles", "OUT", "AIRTIME"),
        ("Customer Withdrawal at Agent Till 98765 - JOYCE SHOP", "OUT", "WITHDRAWAL"),
        ("Deposit of Funds at Agent Till 11111 - DUKA", "IN", "DEPOSIT"),
        ("M-Shwari Deposit", "OUT", "SAVINGS_DEPOSIT"),
        ("M-Shwari Withdraw", "IN", "SAVINGS_WITHDRAWAL"),
        ("M-Shwari Loan Disbursement", "IN", "LOAN_DISBURSEMENT"),
        ("M-Shwari Loan Repayment", "OUT", "LOAN_REPAYMENT"),
        ("OD Loan Repayment to 232323 - Fuliza M-PESA", "OUT", "FULIZA_REPAY"),
        ("Overdraft of Credit Party - Fuliza M-PESA", "IN", "FULIZA_DRAW"),
        ("Customer Transfer of Funds Charge", "OUT", "CHARGES"),
        ("Pay Bill Charge", "OUT", "CHARGES"),
    ])
    def test_categories(self, details, direction, expected):
        category, _ = categorize(details, direction)
        assert category == expected

    def test_counterparty_extraction(self):
        _, counterparty = categorize("Pay Bill to 888880 - KPLC PREPAID Acc. 1234", "OUT")
        assert counterparty == "KPLC PREPAID"

    def test_every_category_has_projection(self):
        from ingestion.mpesa import CATEGORIES
        assert set(CATEGORIES) == set(PROJECTION_CATEGORY.keys())
        assert PROJECTION_CATEGORY["BETTING"] == "BETTING"   # base scorer pattern hook
        assert PROJECTION_CATEGORY["SALARY"] == "SALARY"


class TestPdfDispatch:
    def test_pdf_magic_routes_to_pdf_parser(self):
        # Not a real PDF beyond magic bytes — must fail loudly, not fall through to CSV.
        with pytest.raises(StatementParseError):
            parse_statement(b"%PDF-1.7 garbage", "statement.pdf")

    def test_misnamed_pdf_rejected(self):
        with pytest.raises(StatementParseError):
            parse_statement(b"not,a,pdf", "statement.pdf")
