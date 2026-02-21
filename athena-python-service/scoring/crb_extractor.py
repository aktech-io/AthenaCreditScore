from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class CrbMetrics:
    crb_name: str
    bureau_score: int
    bureau_score_pts: float     # 0-100 mapped
    npa_count: int
    npa_outstanding: float
    npa_pts: float              # -20 to +30
    active_defaults: int
    settled_defaults: int
    default_pts: float          # -30 to +20
    enquiries_90d: int
    applications_12m: int
    report_date: str
    crb_contribution: float     # 0-150 total


def extract_crb_metrics(raw_report: Dict[str, Any]) -> CrbMetrics:
    """
    Extract and score metrics from a raw CRB JSON report.
    Implements the Athena CRB Scorecard (white paper Table 5.2.1).
    """
    credit_report = raw_report.get("creditReport", {})
    crb_name = credit_report.get("bureauName", "Unknown")
    report_date = credit_report.get("reportDate", "N/A")

    # ── 1. Bureau Score → 0-100 pts ────────────────────────────────────────
    bureau_score = credit_report.get("bureauScore", 0) or 0
    # Map from typical Kenya bureau range 300-900 → 0-100
    bureau_score_pts = max(0.0, min(100.0, (bureau_score - 300) / 600 * 100))

    # ── 2. Non-Performing Accounts → -20 to +30 pts ────────────────────────
    npa_accounts = credit_report.get("nonPerformingAccounts", [])
    npa_count = len(npa_accounts)
    npa_outstanding = sum(
        float(a.get("currentBalance", 0) or 0) for a in npa_accounts
    )

    if npa_count == 0:
        npa_pts = 30.0
    elif npa_count <= 2:
        npa_pts = 10.0
    else:
        npa_pts = -20.0

    # ── 3. Default History → -30 to +20 pts ────────────────────────────────
    performing_with_default = credit_report.get("performingAccountsWithDefault", [])
    active_defaults = sum(
        1 for a in performing_with_default
        if str(a.get("status", "")).upper() in {"ACTIVE", "DELINQUENT"}
    )
    settled_defaults = sum(
        1 for a in performing_with_default
        if str(a.get("status", "")).upper() in {"CLOSED", "SETTLED", "PAID"}
    )

    if active_defaults == 0 and settled_defaults == 0:
        default_pts = 20.0
    elif active_defaults == 0 and settled_defaults > 0:
        default_pts = 0.0   # settled = neutral
    else:
        default_pts = -30.0

    # ── Enquiries ───────────────────────────────────────────────────────────
    enquiries_90d = credit_report.get("enquiriesLast90Days", 0) or 0
    applications_12m = credit_report.get("creditApplicationsLast12Months", 0) or 0

    crb_contribution = max(0.0, min(150.0, bureau_score_pts + npa_pts + default_pts))

    return CrbMetrics(
        crb_name=crb_name,
        bureau_score=bureau_score,
        bureau_score_pts=round(bureau_score_pts, 2),
        npa_count=npa_count,
        npa_outstanding=round(npa_outstanding, 2),
        npa_pts=npa_pts,
        active_defaults=active_defaults,
        settled_defaults=settled_defaults,
        default_pts=default_pts,
        enquiries_90d=enquiries_90d,
        applications_12m=applications_12m,
        report_date=report_date,
        crb_contribution=round(crb_contribution, 2),
    )
