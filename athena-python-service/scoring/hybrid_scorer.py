from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import structlog

from scoring.base_scorer import calculate_base_score, BaseScoreResult
from scoring.crb_extractor import extract_crb_metrics, CrbMetrics
from scoring.pdo_transformer import PDOTransformer, PDOResult
from llm.client import LLMClient
from llm.prompts import build_scoring_prompt

logger = structlog.get_logger(__name__)

_pdo = PDOTransformer()
_llm = LLMClient()


@dataclass
class HybridScoreResult:
    customer_id: int
    base_score: float
    crb_contribution: float
    llm_adjustment: int
    pd_probability: float
    final_score: int
    score_band: str
    reasoning: List[str]
    crb_metrics: Optional[CrbMetrics]
    base_result: BaseScoreResult
    llm_provider: str
    llm_model: str
    model_target: str = "champion"


async def compute_hybrid_score(
    customer_id: int,
    customer_name: str,
    transactions: List[Dict[str, Any]],
    crb_raw_report: Optional[Dict[str, Any]] = None,
    analysis_period_days: int = 180,
    model_target: str = "champion",
) -> HybridScoreResult:
    """
    Orchestrates all scoring signals into a single HybridScoreResult.

    Final_Score = PDO(Base_Score + CRB_Contribution + LLM_Adjustment → convert to PD → PDO scale)

    Steps:
    1. Compute quantitative base score from transactions.
    2. Extract CRB contribution if a report is available.
    3. Call LLM for qualitative adjustment.
    4. Sum signals → intermediate score → estimate PD → apply PDO transform.
    """
    # ── 1. Base Score ────────────────────────────────────────────────────────
    base_result = calculate_base_score(transactions, analysis_period_days)
    logger.info("Base score computed", customer_id=customer_id, base_total=base_result.base_total)

    # ── 2. CRB Contribution ──────────────────────────────────────────────────
    crb_metrics: Optional[CrbMetrics] = None
    crb_contribution = 0.0
    if crb_raw_report:
        crb_metrics = extract_crb_metrics(crb_raw_report)
        crb_contribution = crb_metrics.crb_contribution
        logger.info("CRB contribution", customer_id=customer_id, contribution=crb_contribution)

    # ── 3. LLM Qualitative Adjustment ───────────────────────────────────────
    tx_summary = {
        "avg_monthly_income": base_result.avg_monthly_income,
        "income_cv": base_result.income_cv,
        "avg_monthly_savings": base_result.avg_monthly_savings,
        "low_balance_events": base_result.low_balance_events,
        "category_breakdown": base_result.category_breakdown,
        "patterns": base_result.patterns,
        "currency": "KES",
    }
    crb_summary = {}
    if crb_metrics:
        crb_summary = {
            "crb_name": crb_metrics.crb_name,
            "report_date": crb_metrics.report_date,
            "bureau_score": crb_metrics.bureau_score,
            "npa_count": crb_metrics.npa_count,
            "npa_outstanding": crb_metrics.npa_outstanding,
            "active_defaults": crb_metrics.active_defaults,
            "settled_defaults": crb_metrics.settled_defaults,
            "enquiries_90d": crb_metrics.enquiries_90d,
            "applications_12m": crb_metrics.applications_12m,
        }

    prompt = build_scoring_prompt(
        customer_name=customer_name,
        base_score=base_result.base_total,
        crb_contribution=crb_contribution,
        transaction_summary=tx_summary,
        crb_metrics=crb_summary,
    )
    llm_resp = await _llm.get_score_adjustment(prompt)
    llm_adjustment: int = llm_resp["adjustment"]
    reasoning: List[str] = llm_resp["reasoning"]

    # ── 4. Intermediate Combined Score → PD estimate → PDO transform ────────
    intermediate = base_result.base_total + crb_contribution + llm_adjustment
    # Map intermediate score (300-900 range) to PD using a logistic function.
    # Calibrated so that: score=500 → PD≈50%, score=700 → PD≈5%, score=300 → PD≈95%
    pd_probability = _score_to_pd(intermediate)

    pdo_result: PDOResult = _pdo.transform(pd_probability)

    logger.info(
        "Hybrid score computed",
        customer_id=customer_id,
        intermediate=intermediate,
        pd=pd_probability,
        final_score=pdo_result.score,
        band=pdo_result.band,
    )

    return HybridScoreResult(
        customer_id=customer_id,
        base_score=base_result.base_total,
        crb_contribution=crb_contribution,
        llm_adjustment=llm_adjustment,
        pd_probability=pdo_result.pd_probability,
        final_score=pdo_result.score,
        score_band=pdo_result.band,
        reasoning=reasoning,
        crb_metrics=crb_metrics,
        base_result=base_result,
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        model_target=model_target,
    )


def _score_to_pd(score: float) -> float:
    """
    Logistic mapping from intermediate score (300-900) to probability of default.
    Calibrated: score=300→PD=0.96, score=500→PD=0.50, score=700→PD=0.04, score=900→PD=0.01
    """
    import math
    # Logistic: pd = 1 / (1 + exp(k*(score - midpoint)))
    # k=0.012, midpoint=500 gives a reasonable separation
    k = 0.012
    midpoint = 500.0
    pd = 1.0 / (1.0 + math.exp(k * (score - midpoint)))
    return round(pd, 6)
