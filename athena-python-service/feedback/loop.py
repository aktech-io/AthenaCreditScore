from __future__ import annotations

import os
from datetime import date, timedelta
from typing import List, Any

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
        rows = await db.execute(text("""
            SELECT cse.pd_probability, CASE WHEN l.status = 'DEFAULT' THEN 1 ELSE 0 END AS actual
            FROM credit_score_events cse
            JOIN loans l ON l.score_event_id = cse.event_id
            WHERE cse.scored_at >= :window_start AND l.status IN ('DEFAULT','CLOSED')
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

        # ── Trigger retraining if thresholds crossed ──────────────────────────
        should_retrain = ks_drop > KS_DROP_THRESHOLD or psi_val > PSI_THRESHOLD
        if should_retrain:
            logger.warning(
                "Drift detected — retraining triggered",
                ks_drop=ks_drop, psi=psi_val,
            )
            # In production: load full feature dataset and call train_and_register
            # Here we log the trigger — actual training is a background job
            await db.execute(text("""
                INSERT INTO data_quality_log (batch_date, table_name, field_name, missing_count)
                VALUES (:dt, 'model_versions', 'retraining_trigger', 1)
            """), {"dt": date.today()})
            await db.commit()
        else:
            logger.info("No retraining needed", ks_drop=ks_drop, psi=psi_val)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    # Run every Sunday at 02:00 EAT
    scheduler.add_job(run_feedback_loop, "cron", day_of_week="sun", hour=2, minute=0)
    scheduler.start()
    logger.info("Feedback loop scheduler started")
    return scheduler
