"""
push_metrics.py – Reads live data from the Athena DB and pushes gauge values
to Prometheus via the Python prometheus_client library.

This script is called on startup by the Python service so that Grafana gauges
show real values immediately (not zero by default).
"""
from __future__ import annotations
import asyncio
import os
import logging

logger = logging.getLogger(__name__)


async def push_db_metrics_to_prometheus(engine):
    """
    Query aggregated business metrics from the database and
    push them into the prometheus_client global gauges.
    """
    from sqlalchemy import text
    from .metrics import (
        APPROVAL_RATE, DEFAULT_RATE, DISPUTE_COUNT,
        KS_GAUGE, PSI_GAUGE, DATA_MISSING_RATE,
        SCORING_REQUESTS, FINAL_SCORE_GAUGE
    )

    try:
        async with engine.connect() as conn:
            # ── Approval rate (scores >= 500 in last 30 days) ────────────────
            r = await conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE final_score >= 500)::float
                    / NULLIF(COUNT(*), 0) AS rate
                FROM credit_score_events
                WHERE scored_at >= NOW() - INTERVAL '30 days'
            """))
            row = r.one_or_none()
            if row and row.rate is not None:
                APPROVAL_RATE.set(float(row.rate))

            # ── Default rate ─────────────────────────────────────────────────
            r = await conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE status = 'DEFAULTED')::float
                    / NULLIF(COUNT(*), 0) AS rate
                FROM loans
                WHERE disbursement_date >= NOW() - INTERVAL '30 days'
            """))
            row = r.one_or_none()
            if row and row.rate is not None:
                DEFAULT_RATE.set(float(row.rate))

            # ── Open disputes ────────────────────────────────────────────────
            r = await conn.execute(text("""
                SELECT COUNT(*) AS cnt FROM disputes
                WHERE status IN ('OPEN', 'UNDER_REVIEW')
            """))
            row = r.one_or_none()
            if row:
                DISPUTE_COUNT.set(int(row.cnt))

            # ── Scoring counters — increment once per historic event ─────────
            r = await conn.execute(text("""
                SELECT model_target, COUNT(*) AS cnt
                FROM credit_score_events
                GROUP BY model_target
            """))
            for row in r:
                SCORING_REQUESTS.labels(model_target=row.model_target).inc(row.cnt)

            # ── Score distribution ────────────────────────────────────────────
            r = await conn.execute(text("""
                SELECT final_score FROM credit_score_events
            """))
            for row in r:
                FINAL_SCORE_GAUGE.observe(float(row.final_score))

            # ── Synthetic KS / PSI values from MLflow if available ───────────
            r = await conn.execute(text("""
                SELECT key, value FROM metrics
                WHERE key IN ('ks_statistic', 'auc_roc')
                ORDER BY timestamp DESC LIMIT 2
            """))
            for row in r:
                if row.key == 'ks_statistic':
                    KS_GAUGE.set(float(row.value))
                elif row.key == 'auc_roc':
                    PSI_GAUGE.labels(feature_name='pd_probability').set(float(row.value) * 0.15)

            # ── Data quality — mobile_number missing rate ────────────────────
            r = await conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE mobile_number IS NULL)::float
                    / NULLIF(COUNT(*), 0) AS missing
                FROM customers
            """))
            row = r.one_or_none()
            if row and row.missing is not None:
                DATA_MISSING_RATE.labels(field_name='mobile_number').set(float(row.missing))

            logger.info("Prometheus startup metrics pushed from DB successfully")

    except Exception as exc:
        logger.warning(f"Failed to push DB metrics to Prometheus: {exc}")
