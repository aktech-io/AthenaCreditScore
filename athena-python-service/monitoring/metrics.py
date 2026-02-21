from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from fastapi.responses import Response

metrics_router = APIRouter()

# ── Scoring metrics ──────────────────────────────────────────────────────────
SCORING_REQUESTS = Counter(
    "athena_scoring_requests_total",
    "Total number of scoring requests processed",
    ["model_target"],
)
SCORING_LATENCY = Histogram(
    "athena_scoring_latency_seconds",
    "Time taken to complete a scoring request",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)
FINAL_SCORE_GAUGE = Histogram(
    "athena_final_score_distribution",
    "Distribution of final PDO credit scores",
    buckets=[300, 400, 500, 550, 600, 640, 680, 720, 780, 850],
)
PD_GAUGE = Histogram(
    "athena_pd_probability_distribution",
    "Distribution of raw PD probabilities",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
)

# ── Model drift metrics ──────────────────────────────────────────────────────
PSI_GAUGE = Gauge(
    "athena_psi_value",
    "Population Stability Index for each feature",
    ["feature_name"],
)
KS_GAUGE = Gauge(
    "athena_ks_statistic",
    "Current KS statistic vs. training baseline",
)

# ── Business metrics ─────────────────────────────────────────────────────────
APPROVAL_RATE = Gauge(
    "athena_approval_rate_30d",
    "30-day loan approval rate (score >= 500)",
)
DEFAULT_RATE = Gauge(
    "athena_default_rate_30d",
    "30-day portfolio default rate",
)
DISPUTE_COUNT = Gauge(
    "athena_open_disputes_count",
    "Number of open customer disputes",
)

# ── Data quality ─────────────────────────────────────────────────────────────
DATA_MISSING_RATE = Gauge(
    "athena_data_missing_rate",
    "Missing data rate for a given field",
    ["field_name"],
)


@metrics_router.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics in text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
