from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, List, Optional

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from db.database import AsyncSessionLocal
from mlops.trainer import train_and_register

logger = structlog.get_logger(__name__)

PSI_THRESHOLD = float(os.getenv("PSI_THRESHOLD", "0.2"))
KS_DROP_THRESHOLD = float(os.getenv("KS_DROP_THRESHOLD", "0.05"))


def compute_psi(base: List[float], current: List[float], buckets: int = 10) -> float:
    """Compute Population Stability Index between base and current distributions."""
    import numpy as np
    base_arr = np.array(base)
    cur_arr = np.array(current)
    bins = np.percentile(base_arr, np.linspace(0, 100, buckets + 1))
    bins[0] -= 1e-9
    bins[-1] += 1e-9

    base_pcts = np.histogram(base_arr, bins=bins)[0] / len(base_arr)
    cur_pcts = np.histogram(cur_arr, bins=bins)[0] / len(cur_arr)

    # Avoid division by zero
    base_pcts = np.where(base_pcts == 0, 1e-4, base_pcts)
    cur_pcts = np.where(cur_pcts == 0, 1e-4, cur_pcts)

    return float(np.sum((cur_pcts - base_pcts) * np.log(cur_pcts / base_pcts)))


async def run_feedback_loop():
    """
    Weekly adaptive feedback loop:
    1. Compute KS on sliding 30-day window of scored loans vs outcomes.
    2. Compute PSI for key features.
    3. Trigger retraining if drift is detected.
    4. Log findings.
    """
    logger.info("Feedback loop started")
    async with AsyncSessionLocal() as db:
        # ── KS on recent predictions ─────────────────────────────────────────
        window_start = date.today() - timedelta(days=30)
        # Note: seeded data uses status 'DEFAULTED'; accept both spellings.
        rows = await db.execute(text("""
            SELECT cse.pd_probability, CASE WHEN l.status LIKE 'DEFAULT%' THEN 1 ELSE 0 END AS actual
            FROM credit_score_events cse
            JOIN loans l ON l.score_event_id = cse.event_id
            WHERE cse.scored_at >= :window_start AND l.status IN ('DEFAULT','DEFAULTED','CLOSED')
        """), {"window_start": window_start})
        results = rows.fetchall()

        if len(results) < 50:
            logger.info("Not enough outcomes for feedback loop yet", count=len(results))
            return

        y_prob = [r[0] for r in results]
        y_true = [r[1] for r in results]

        from mlops.trainer import ks_statistic
        current_ks = ks_statistic(y_true, y_prob)

        # Get last model version KS
        mv_row = await db.execute(text(
            "SELECT ks_statistic FROM model_versions WHERE alias='champion' ORDER BY trained_at DESC LIMIT 1"
        ))
        last_mv = mv_row.fetchone()
        baseline_ks = float(last_mv[0]) if last_mv and last_mv[0] else 0.30

        ks_drop = baseline_ks - current_ks
        logger.info("KS check", baseline=baseline_ks, current=current_ks, drop=ks_drop)

        # ── PSI for key features ──────────────────────────────────────────────
        # Simplified: compute PSI on pd_probability distribution
        base_rows = await db.execute(text("""
            SELECT pd_probability FROM credit_score_events
            WHERE scored_at < :window_start ORDER BY RANDOM() LIMIT 500
        """), {"window_start": window_start})
        base_probs = [r[0] for r in base_rows.fetchall()]
        psi_val = compute_psi(base_probs, y_prob) if len(base_probs) >= 20 else 0.0

        await db.execute(text("""
            INSERT INTO psi_monitoring (feature_name, psi_value, sample_date, alert_triggered)
            VALUES ('pd_probability', :psi, :dt, :alert)
        """), {"psi": psi_val, "dt": date.today(), "alert": psi_val > PSI_THRESHOLD})
        await db.commit()

        # ── Feature-level PSI vs training baseline (Phase 3 governance) ───────
        feature_psi = await compute_feature_level_psi(db, window_start)
        max_feature_psi = max(feature_psi.values(), default=0.0)

        # ── Trigger retraining if thresholds crossed ──────────────────────────
        should_retrain = (
            ks_drop > KS_DROP_THRESHOLD
            or psi_val > PSI_THRESHOLD
            or max_feature_psi > PSI_THRESHOLD
        )
        if should_retrain:
            logger.warning(
                "Drift detected — training challenger",
                ks_drop=ks_drop, psi=psi_val, max_feature_psi=max_feature_psi,
            )
            await db.execute(text("""
                INSERT INTO data_quality_log (batch_date, table_name, field_name, missing_count)
                VALUES (:dt, 'model_versions', 'retraining_trigger', 1)
            """), {"dt": date.today()})
            await db.commit()
            await train_challenger(db)
        else:
            logger.info("No retraining needed", ks_drop=ks_drop, psi=psi_val)


async def compute_feature_level_psi(db, window_start) -> dict:
    """
    Feature-level PSI (Phase 3): compare the last-30-days lgbm_features
    vectors against the training baseline persisted as an MLflow artifact
    (feature_baseline.json) at train time. Sets the per-feature Prometheus
    gauge and persists psi_monitoring rows. Best-effort — returns {} when the
    baseline or recent vectors are unavailable.
    """
    import asyncio

    from features.pipeline import LGBM_FEATURE_SET
    from monitoring.feature_psi import (
        compute_feature_psi,
        load_training_baseline,
        set_feature_psi_gauges,
    )

    try:
        baseline = await asyncio.to_thread(load_training_baseline)
        if not baseline:
            logger.info("No feature PSI baseline available — skipping feature-level PSI")
            return {}

        rows = await db.execute(text("""
            SELECT fv.feature_vector
            FROM feature_values fv
            JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
            WHERE fd.feature_set_name = :fset AND fv.computed_at >= :window_start
        """), {"fset": LGBM_FEATURE_SET, "window_start": window_start})
        current: dict = {}
        n_vectors = 0
        for (fv,) in rows.fetchall():
            vec = fv if isinstance(fv, dict) else __import__("json").loads(fv)
            n_vectors += 1
            for name, value in vec.items():
                if isinstance(value, (int, float)):
                    current.setdefault(name, []).append(float(value))
        if n_vectors < 20:
            logger.info("Too few recent feature vectors for feature-level PSI",
                        n_vectors=n_vectors)
            return {}

        feature_psi = compute_feature_psi(baseline, current)
        set_feature_psi_gauges(feature_psi)
        for name, value in feature_psi.items():
            await db.execute(text("""
                INSERT INTO psi_monitoring (feature_name, psi_value, sample_date, alert_triggered)
                VALUES (:name, :psi, :dt, :alert)
            """), {"name": name, "psi": value, "dt": date.today(),
                   "alert": value > PSI_THRESHOLD})
        await db.commit()

        drifted = {k: v for k, v in feature_psi.items() if v > PSI_THRESHOLD}
        logger.info("Feature-level PSI computed",
                    n_features=len(feature_psi), n_vectors=n_vectors,
                    drifted=list(drifted) or None)
        return feature_psi
    except Exception as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.warning("Feature-level PSI failed — continuing loop", error=str(exc))
        return {}


MIN_TRAINING_ROWS = int(os.getenv("MIN_TRAINING_ROWS", "200"))


def _vec_to_row(fv, label, ts, feature_names) -> dict:
    vec = fv if isinstance(fv, dict) else __import__("json").loads(fv)
    row = {name: vec.get(name, 0.0) for name in feature_names}
    row["default_flag"] = int(label)
    row["scored_at_ts"] = float(ts)
    return row


async def build_training_frame(db) -> Optional["pd.DataFrame"]:
    """
    Assemble a training frame (v2): one row per resolved loan, joining the
    customer's stored lgbm_features vector with the outcome label.

    Label sources, in order of preference:
      1. `training_labels` — real LMS repayment outcomes captured by
         listeners/loan_outcomes.py. Terminal outcome per loan_ref =
         MAX(default_flag) across its events (a written-off loan stays bad
         even if a loan.closed event also arrived).
      2. `loans.status` heuristic (DEFAULT% → 1) — only for customers with
         no real label at all.

    The mix is recorded on df.attrs["label_mix"] and logged as MLflow params
    by train_and_register.

    Caveat (documented in features/pipeline.py): vectors are as-of-now, not
    as-of-application, so historical labels carry temporal leakage. Acceptable
    to keep the pipeline exercised end-to-end; feature snapshots at scoring
    time fix it.
    """
    import pandas as pd
    from features.pipeline import LGBM_FEATURE_SET, FEATURE_NAMES

    records = []
    n_real = 0

    # ── 1. Real outcomes from LMS loan lifecycle events ──────────────────────
    try:
        real_rows = await db.execute(text("""
            SELECT fv.feature_vector,
                   tl.default_flag,
                   EXTRACT(EPOCH FROM tl.observed_at) AS scored_at_ts
            FROM (
                SELECT customer_id, loan_ref,
                       MAX(default_flag) AS default_flag,
                       MAX(observed_at)  AS observed_at
                FROM training_labels
                GROUP BY customer_id, loan_ref
            ) tl
            JOIN feature_values fv ON fv.customer_id = tl.customer_id
            JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
            WHERE fd.feature_set_name = :fset
        """), {"fset": LGBM_FEATURE_SET})
        for fv, label, ts in real_rows.fetchall():
            records.append(_vec_to_row(fv, label, ts, FEATURE_NAMES))
        n_real = len(records)
    except Exception as exc:
        # training_labels not migrated yet — heuristic-only, don't crash the loop.
        await db.rollback()
        logger.warning("training_labels unavailable — heuristic labels only",
                       error=str(exc))

    # ── 2. Heuristic fallback for customers without any real label ───────────
    heur_rows = await db.execute(text("""
        SELECT fv.feature_vector,
               CASE WHEN l.status LIKE 'DEFAULT%' THEN 1 ELSE 0 END AS default_flag,
               EXTRACT(EPOCH FROM l.created_at) AS scored_at_ts
        FROM loans l
        JOIN feature_values fv ON fv.customer_id = l.customer_id
        JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
        WHERE l.status IN ('DEFAULT', 'DEFAULTED', 'CLOSED')
          AND fd.feature_set_name = :fset
          AND NOT EXISTS (
              SELECT 1 FROM training_labels tl WHERE tl.customer_id = l.customer_id
          )
    """) if n_real else text("""
        SELECT fv.feature_vector,
               CASE WHEN l.status LIKE 'DEFAULT%' THEN 1 ELSE 0 END AS default_flag,
               EXTRACT(EPOCH FROM l.created_at) AS scored_at_ts
        FROM loans l
        JOIN feature_values fv ON fv.customer_id = l.customer_id
        JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
        WHERE l.status IN ('DEFAULT', 'DEFAULTED', 'CLOSED')
          AND fd.feature_set_name = :fset
    """), {"fset": LGBM_FEATURE_SET})
    for fv, label, ts in heur_rows.fetchall():
        records.append(_vec_to_row(fv, label, ts, FEATURE_NAMES))
    n_heuristic = len(records) - n_real

    label_mix = {"n_real_labels": n_real, "n_heuristic": n_heuristic}
    logger.info("Training frame label mix", **label_mix)

    if len(records) < MIN_TRAINING_ROWS:
        logger.info("Not enough labeled rows for retraining", rows=len(records))
        return None
    df = pd.DataFrame(records)
    if df["default_flag"].nunique() < 2:
        logger.info("Single-class label distribution — cannot train")
        return None
    df.attrs["label_mix"] = label_mix
    return df


async def train_challenger(db) -> Optional[str]:
    """
    Train and register a CHALLENGER. Promotion to champion is intentionally
    not automated — it requires human review of the MLflow run (SR 11-7).
    """
    import asyncio

    df = await build_training_frame(db)
    if df is None:
        return None
    run_id = await asyncio.to_thread(
        train_and_register, df, "default_flag", "challenger", None, "scored_at_ts",
        df.attrs.get("label_mix"),
    )
    logger.warning(
        "Challenger trained and registered — awaiting human review for promotion",
        run_id=run_id, rows=len(df),
    )
    return run_id


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    # Run every Sunday at 02:00 EAT
    scheduler.add_job(run_feedback_loop, "cron", day_of_week="sun", hour=2, minute=0)
    scheduler.start()
    logger.info("Feedback loop scheduler started")
    return scheduler
