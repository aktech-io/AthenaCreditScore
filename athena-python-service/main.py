from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from auth.jwt_handler import jwt_router
from api.credit_reports import router as credit_reports_router
from api.scoring import router as scoring_router
from api.statements import router as statements_router
from api.decisioning import router as decisioning_router
from api.simulator import router as simulator_router
from api.collections import router as collections_router
from api.alerts import router as alerts_router
from api.privacy import router as privacy_router
from monitoring.metrics import metrics_router
from db.database import init_db


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Start APScheduler jobs
    from feedback.loop import start_scheduler
    scheduler = start_scheduler()
    # LMS loan-outcome listener (training labels) — no-op if RABBITMQ_URL unset
    from listeners.loan_outcomes import start_loan_outcomes_listener, stop_loan_outcomes_listener
    loan_outcomes_task = start_loan_outcomes_listener()
    yield
    await stop_loan_outcomes_listener(loan_outcomes_task)
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="NemoScore — AI/ML Scoring Service",
    description="MCP server, hybrid scoring engine, feature store, and MLOps for NemoScore (Nemo neobank).",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jwt_router, prefix="/auth", tags=["Auth"])
app.include_router(credit_reports_router, prefix="/api/v1", tags=["Credit Reports"])
app.include_router(scoring_router, prefix="/api/v1", tags=["Scoring"])
app.include_router(statements_router, prefix="/api/v1", tags=["Statements"])
app.include_router(decisioning_router, prefix="/api/v1", tags=["Decisioning"])
app.include_router(simulator_router, prefix="/api/v1", tags=["Simulator"])
app.include_router(collections_router, prefix="/api/v1", tags=["Collections"])
app.include_router(alerts_router, prefix="/api/v1", tags=["Alerts"])
app.include_router(privacy_router, prefix="/api/v1", tags=["Privacy"])
app.include_router(metrics_router, tags=["Metrics"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "athena-python-service"}
