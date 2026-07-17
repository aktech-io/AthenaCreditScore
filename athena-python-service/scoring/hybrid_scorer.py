from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import structlog

from scoring.base_scorer import calculate_base_score, BaseScoreResult
from scoring.crb_extractor import extract_crb_metrics, CrbMetrics
from scoring.pdo_transformer import PDOTransformer, PDOResult
from scoring.lgbm_scorer import get_lgbm_scorer
from llm.client import LLMClient
from llm.prompts import build_scoring_prompt

logger = structlog.get_logger(__name__)

_pdo = PDOTransformer()
_llm = LLMClient()

# The LLM is a bounded qualitative overlay: capped, and never allowed to move a
# score across a band boundary. The PD itself is never touched by the LLM.
LLM_MAX_ADJUSTMENT = int(os.getenv("LLM_MAX_ADJUSTMENT", "25"))
MIN_MONTHS_FULL = int(os.getenv("MIN_MONTHS_FULL_HISTORY", "3"))


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
    pd_source: str = "scorecard"
    model_version: Optional[str] = None
    data_sufficiency: str = "FULL"       # FULL | PARTIAL | INSUFFICIENT
    status: str = "SCORED"               # SCORED | INSUFFICIENT_DATA


async def compute_hybrid_score(
    customer_id: int,
    customer_name: str,
    transactions: List[Dict[str, Any]],
    crb_raw_report: Optional[Dict[str, Any]] = None,
    analysis_period_days: int = 180,
    model_target: str = "champion",
    features: Optional[Dict[str, Any]] = None,
) -> HybridScoreResult:
    """
    Orchestrates all scoring signals into a single HybridScoreResult.

    PD source, in priority order:
    1. LightGBM model from the MLflow registry (champion or challenger alias),
       when a feature vector is available and the model is loaded.
    2. Rule-based scorecard (base score + CRB contribution → logistic PD).

    The PD is transformed to a 300-850 score via PDO. The LLM adjustment is a
    capped, within-band overlay on the score — it never changes the PD.
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

    # ── 3. Data sufficiency ──────────────────────────────────────────────────
    months = base_result.months_of_history
    if months >= MIN_MONTHS_FULL:
        data_sufficiency = "FULL"
    elif crb_metrics is not None and crb_metrics.bureau_score > 0:
        data_sufficiency = "PARTIAL"   # thin transaction file, bureau data present
    else:
        data_sufficiency = "INSUFFICIENT"
    status = "SCORED" if data_sufficiency != "INSUFFICIENT" else "INSUFFICIENT_DATA"

    # ── 4. Probability of default ────────────────────────────────────────────
    pd_source = "scorecard"
    model_version: Optional[str] = None
    pd_probability: Optional[float] = None

    if features:
        scorer = get_lgbm_scorer(model_target)
        ml_pd = scorer.predict_pd(features)
        if ml_pd is not None:
            pd_probability = round(ml_pd, 6)
            pd_source = f"lgbm:{model_target}"
            model_version = scorer.model_version

    if pd_probability is None:
        intermediate = base_result.base_total + crb_contribution
        pd_probability = _score_to_pd(intermediate)

    pdo_result: PDOResult = _pdo.transform(pd_probability)
    quant_score = pdo_result.score

    # ── 5. LLM Qualitative Overlay (capped, within-band) ─────────────────────
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
    raw_adjustment: int = llm_resp["adjustment"]
    reasoning: List[str] = llm_resp["reasoning"]

    llm_adjustment = apply_llm_overlay_bounds(quant_score, raw_adjustment)
    if llm_adjustment != raw_adjustment:
        logger.info(
            "LLM adjustment clamped",
            customer_id=customer_id, raw=raw_adjustment, applied=llm_adjustment,
        )

    final_score = quant_score + llm_adjustment
    score_band = _pdo._get_band(final_score)

    logger.info(
        "Hybrid score computed",
        customer_id=customer_id,
        pd=pd_probability,
        pd_source=pd_source,
        quant_score=quant_score,
        llm_adjustment=llm_adjustment,
        final_score=final_score,
        band=score_band,
        status=status,
    )

    return HybridScoreResult(
        customer_id=customer_id,
        base_score=base_result.base_total,
        crb_contribution=crb_contribution,
        llm_adjustment=llm_adjustment,
        pd_probability=pd_probability,
        final_score=final_score,
        score_band=score_band,
        reasoning=reasoning,
        crb_metrics=crb_metrics,
        base_result=base_result,
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        model_target=model_target,
        pd_source=pd_source,
        model_version=model_version,
        data_sufficiency=data_sufficiency,
        status=status,
    )


def apply_llm_overlay_bounds(quant_score: int, adjustment: int) -> int:
    """
    Bound the LLM adjustment: hard cap at ±LLM_MAX_ADJUSTMENT, and clamp so the
    adjusted score stays inside the band of the quantitative score.
    """
    capped = max(-LLM_MAX_ADJUSTMENT, min(LLM_MAX_ADJUSTMENT, adjustment))
    floor, ceiling = PDOTransformer.band_bounds(quant_score)
    adjusted = max(floor, min(ceiling, quant_score + capped))
    return adjusted - quant_score


def _score_to_pd(score: float) -> float:
    """
    Fallback logistic mapping from scorecard points (300-900) to PD, used only
    when no registered ML model is available. NOTE: this curve is heuristic and
    not calibrated to observed defaults — Phase 1 replaces it entirely.
    """
    import math
    k = 0.012
    midpoint = 500.0
    pd = 1.0 / (1.0 + math.exp(k * (score - midpoint)))
    return round(pd, 6)
