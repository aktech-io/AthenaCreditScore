from __future__ import annotations

"""
Phase 4 score simulator (contract: docs/nemoscore-api.yaml 1.4.0):

  POST /api/v1/credit-score/{customer_id}/simulate

Maps what-if deltas onto a COPY of the customer's current lgbm_features
vector and runs them through the ACTUAL champion model + calibrator + PDO
transform (scoring/lgbm_scorer.py). Falls back to a base-scorecard recompute
over delta-modified transactions when no feature vector or registered model
exists. Strictly read-only: no score events are written, stored features are
never mutated, and the DB session is never committed.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.scoring import _check_access
from auth.jwt_handler import verify_jwt_or_service_key
from db.database import get_db
from scoring.pdo_transformer import PDOTransformer
from scoring.simulator import (
    SUPPORTED_DELTAS,
    apply_deltas,
    apply_deltas_to_transactions,
    normalize_deltas,
)

router = APIRouter()
_pdo = PDOTransformer()


class SimulateRequest(BaseModel):
    deltas: Dict[str, Any] = Field(
        description="What-if deltas, e.g. {\"clear_delinquencies\": true, "
                    "\"add_monthly_savings\": 5000}")


def _point(pd_probability: float) -> Dict[str, Any]:
    r = _pdo.transform(pd_probability)
    return {"score": r.score, "score_band": r.band, "pd_probability": r.pd_probability}


async def _load_features(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
    """Stored vector if present; else computed on the fly WITHOUT persisting
    (keeps the endpoint read-only)."""
    from features.feature_store import read_features
    from features.pipeline import LGBM_FEATURE_SET, compute_customer_features

    stored = await read_features(db, customer_id, LGBM_FEATURE_SET)
    if stored is not None:
        return stored
    return await compute_customer_features(db, customer_id)


async def _load_transactions(db: AsyncSession, customer_id: int) -> List[Dict[str, Any]]:
    rows = await db.execute(text("""
        SELECT transaction_date, amount, transaction_type, category,
               description, channel, balance_after
        FROM transactions WHERE customer_id = :cid
        ORDER BY transaction_date DESC LIMIT 1000
    """), {"cid": customer_id})
    return [dict(r._mapping) for r in rows.fetchall()]


@router.post("/credit-score/{customer_id}/simulate")
async def simulate_score(
    customer_id: int,
    body: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(verify_jwt_or_service_key),
):
    """Model-backed what-if score simulation (read-only). Added in 1.4.0."""
    _check_access(claims, customer_id)

    applicable, unknown = normalize_deltas(body.deltas)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown delta(s): {sorted(unknown)}. "
                   f"Supported: {sorted(SUPPORTED_DELTAS)}",
        )
    if not applicable:
        raise HTTPException(status_code=422, detail="No effective deltas in request")

    features = await _load_features(db, customer_id)

    # ── Primary path: actual champion model + calibrator + PDO ──────────────
    if features is not None:
        from scoring.lgbm_scorer import get_lgbm_scorer
        scorer = get_lgbm_scorer("champion")
        current_pd = scorer.predict_pd(features)
        if current_pd is not None:
            simulated_features = apply_deltas(features, applicable)
            simulated_pd = scorer.predict_pd(simulated_features)
            if simulated_pd is None:
                raise HTTPException(status_code=502, detail="Model inference failed on simulated vector")

            current = _point(current_pd)
            simulated = _point(simulated_pd)

            impacts = []
            for name, value in applicable.items():
                solo_pd = scorer.predict_pd(apply_deltas(features, {name: value}))
                impacts.append({
                    "delta": name,
                    "value": value,
                    "score_impact": (_pdo.transform(solo_pd).score - current["score"])
                                    if solo_pd is not None else None,
                })
            impacts.sort(key=lambda i: -abs(i["score_impact"] or 0))

            return {
                "customer_id": customer_id,
                "engine": "lgbm:champion",
                "model_version": scorer.model_version,
                "current": current,
                "simulated": simulated,
                "score_delta": simulated["score"] - current["score"],
                "delta_impacts": impacts,
                "no_effect_deltas": [],
                "read_only": True,
            }

    # ── Fallback: base-scorecard recompute over modified transactions ───────
    from scoring.base_scorer import calculate_base_score
    from scoring.hybrid_scorer import _score_to_pd

    transactions = await _load_transactions(db, customer_id)
    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="Insufficient data to simulate — no feature vector, no "
                   "loadable model, and no transactions on record",
        )

    def scorecard_point(txns: List[Dict[str, Any]]) -> Dict[str, Any]:
        base = calculate_base_score(txns)
        return _point(_score_to_pd(base.base_total))

    current = scorecard_point(transactions)
    sim_txns, no_effect = apply_deltas_to_transactions(transactions, applicable)
    simulated = scorecard_point(sim_txns)

    impacts = []
    for name, value in applicable.items():
        if name in no_effect:
            continue
        solo_txns, _ = apply_deltas_to_transactions(transactions, {name: value})
        impacts.append({
            "delta": name,
            "value": value,
            "score_impact": scorecard_point(solo_txns)["score"] - current["score"],
        })
    impacts.sort(key=lambda i: -abs(i["score_impact"] or 0))

    return {
        "customer_id": customer_id,
        "engine": "scorecard",
        "model_version": None,
        "current": current,
        "simulated": simulated,
        "score_delta": simulated["score"] - current["score"],
        "delta_impacts": impacts,
        "no_effect_deltas": sorted(no_effect),
        "read_only": True,
    }
