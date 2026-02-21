# Athena Credit Initiative — Build Prompts (Revised)

> These prompts are ordered for sequential handoff. Each builds on all previous.
> Use with a capable code-generation AI (Claude 3.5 Sonnet, GPT-4o, or Gemini 1.5 Pro recommended).

---

## Prompt 1 — Project Scaffold & Infrastructure

```
You are building the Athena Credit Initiative, an AI-powered credit scoring system for SMEs in Kenya.
Create the following project structure at `/home/adira/AthenaCreditScore/`:

1. `docker-compose.yml` orchestrating: postgres:16, rabbitmq:3.13-management, mlflow (custom Dockerfile), 
   athena-java-service, athena-python-service, prometheus, grafana, kong:3.6.
2. `.env.example` with all environment variables documented inline (see schema below).
3. `database/schema.sql`: 23 PostgreSQL tables including customers, loans, transactions, admin_users,
   credit_score_events, feature_definitions, feature_values, shap_logs, champion_challenger_log, consents,
   disputes, api_keys, audit_log, and notification_events.
4. `mlflow/mlflow.Dockerfile`: Python 3.12-slim, psycopg2-binary, boto3, MLflow 2.13.0, non-root user.

Use snake_case for all table/column names. Include a `CREATE INDEX` for every foreign key.
```

---

## Prompt 2 — Python Service Foundation

```
Build the FastAPI application skeleton for `athena-python-service/`:

1. `main.py`: FastAPI app with lifespan (init DB, start APScheduler), SlowAPI rate limiting 
   (100/min per IP), CORS, and route registration for `/api/v1/credit-reports`, `/api/v1/credit-score`.
2. `db/database.py`: Async SQLAlchemy engine + session factory + `get_db` dependency.
3. `auth/jwt_handler.py`: `verify_jwt` FastAPI dependency that reads `JWT_SECRET` from env.
   Token must carry `sub` (username), `roles` (list), optional `customerId`.
4. `requirements.txt`: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic, structlog,
   slowapi, openai, lightgbm, mlflow, shap, scikit-learn, pandas, numpy, apscheduler,
   prometheus-client, mcp.

Use structlog for all logging.
```

---

## Prompt 3 — Hybrid Scoring Engine (Python)

```
Implement the three-layer hybrid credit scorer in `athena-python-service/scoring/`:

1. `base_scorer.py`: Score from 300-700 using 5 dimensions:
   - Income Stability: 1 − CoV(monthly inflows), max 120 pts
   - Income Level: median monthly net flow vs KES 5K/15K/40K thresholds, max 100 pts
   - Savings Rate: net_inflow/gross_inflow, max 80 pts
   - Low-Balance Events: frequency of balance < KES 500, max 100 pts
   - Transaction Diversity: distinct counter-party categories, max 100 pts
   
2. `crb_extractor.py`: Extract from CRB dict: bureau_score (0-900→0-90pts), 
   npa_count (−15 each), active_default_flag (−40pts). Clamp to [−100, +150].

3. `pdo_transformer.py`: PD → PDO score via:
   `score = BASE_SCORE − (PDO/ln(2)) × ln(pd/(1−pd)/BASE_ODDS)`
   Defaults: BASE_SCORE=500, BASE_ODDS=1.0, PDO=50. Clamp to [300, 850].
   Include inverse method: score → PD.

4. `hybrid_scorer.py`: Orchestrate: transaction data → base_score → CRB contribution →
   LLM adjustment (±50 pts cap) → blend into composite PD → PDO score.
   Return full breakdown dict.
```

---

## Prompt 4 — Feature Engineering (Python)

```
Implement feature engineering modules in `athena-python-service/features/`:

1. `application_features.py`:
   - `capital_growth_ratio`: (current_capital − initial_capital) / initial_capital
   - `revenue_per_employee`: annual_revenue / employee_count (0 if missing)
   - `profit_margin`: net_profit / gross_revenue (clamp to [−1, 1])
   - `sector_density`: fraction of all customers in same sector + region

2. `performance_features.py`: Returns `PerformanceFeatures` dataclass:
   - `max_delinquency_streak`, `current_delinquency_streak`
   - `delinquency_rate_30d/90d/180d` (rolling window from reference_date)
   - `payment_cv` (CoV of payment amounts)
   - `avg_loan_spacing_days`, `min_loan_spacing_days`
   - `early_repayment_rate`, `partial_payment_rate`

3. `categorical_encoder.py`: `TargetEncoder` class with K-fold CV (default 5 folds),
   smoothing (default α=10). Methods: `fit_transform()`, `transform()`, `to_json()`, `from_json()`.

4. `feature_store.py`: Async functions: `register_definition()`, `write_features()`,
   `read_features()`, `read_features_batch()`, `list_feature_sets()`, `get_feature_coverage()`.
   Backed by `feature_definitions` and `feature_values` PostgreSQL tables.
```

---

## Prompt 5 — LLM Integration (Python)

```
Implement the LLM client in `athena-python-service/llm/`:

1. `client.py`: Dual-mode LLM client. Read `LLM_PROVIDER` env var:
   - `"openai"`: use openai.AsyncOpenAI with `OPENAI_API_KEY`
   - `"local"`: use openai.AsyncOpenAI with `base_url=LLM_BASE_URL`, `api_key="unused"`
   Both modes use the same `openai` Python package (Ollama exposes a /v1 compatible endpoint).
   Function: `async get_llm_adjustment(application_context: dict) -> tuple[int, str]`
   Returns (adjustment_pts, reasoning_text).

2. `prompts.py`: System prompt defining the LLM as a senior credit analyst for Kenya.
   User prompt template that injects: sector, region, capital_growth_ratio, revenue_per_employee,
   profit_margin, sector_density, crb_summary.
   Instructs model to return JSON: {"adjustment": <-50 to 50>, "reasoning": "<50 words>"}

Only return numeric adjustment and reasoning — no other fields.
```

---

## Prompt 6 — MLOps Pipeline (Python)

```
Implement MLOps components in `athena-python-service/mlops/`:

1. `trainer.py`: LightGBM training pipeline:
   - Load feature vectors from feature store
   - Stratified 5-fold CV, log AUC-ROC/KS/PR-AUC each fold
   - Compute and log SHAP values as bar chart artifact
   - Register model under `athena_lgbm_scorer` in MLflow registry
   - Tag with `training_date`, `n_samples`, `ks_statistic`

2. `mlflow_client.py`: Functions:
   - `start_run()`, `log_metrics()`, `log_params()`, `log_artifact()`
   - `register_model()`, `promote_to_staging()`, `promote_to_challenger()`
   - `promote_challenger_to_champion()` (demotes old champion)
   - `compare_champion_challenger()` → recommendation: promote/keep/rollback
     (promote if KS ≥ +0.02 or AUC ≥ +0.005)

3. `shap_analyzer.py`: Load last 500 defaulted loan vectors → compute TreeExplainer SHAP →
   rank features by mean |SHAP| → log to MLflow → persist to `shap_logs` table.

4. `feedback/loop.py`: APScheduler weekly cron:
   - Compute PSI on `pd_probability` distribution (train vs recent)
   - Compute KS statistic (approved vs declined)
   - If PSI > 0.2 OR KS drops 0.05: trigger retraining
```

---

## Prompt 7 — APIs & MCP Server (Python)

```
Implement the remaining FastAPI endpoints and MCP server:

1. `api/credit_reports.py`: POST endpoint (X-Api-Key auth):
   Upsert customer → store CRB report → fetch Mifos transactions →
   compute application + performance features → run hybrid scorer →
   persist to credit_score_events → publish to RabbitMQ → return full score dict.

2. `api/scoring.py`: GET endpoints (JWT auth):
   - `/api/v1/credit-score/{customerId}`: summary (score, band, PD)
   - `/api/v1/credit-report/{customerId}`: full breakdown + CRB + LLM reasoning
   Both enforce RBAC: CUSTOMER role can only access own data.

3. `monitoring/metrics.py`: Prometheus metrics (prometheus_client):
   - Counter: scoring_requests_total (model_target label)
   - Histogram: scoring_latency_seconds (buckets: 0.1, 0.5, 1, 2, 5)
   - Gauge: ks_statistic, psi_value (feature_name label)
   - Gauge: default_rate_30d, approval_rate_30d, open_disputes_count
   - Gauge: data_missing_rate (field_name label)

4. `mcp_server.py`: MCP server with 7 tools:
   get_customer_profile, get_transactions_for_analysis, get_previous_decisions,
   calculate_base_score, fetch_crb_report, extract_crb_metrics, calculate_credit_score.
```

---

## Prompt 8 — Java Service Foundation

```
Build the Spring Boot service at `athena-java-service/`:

1. `pom.xml`: Spring Boot 3.2, JPA, Security, WebFlux (WebClient), OpenFeign,
   AMQP, Caffeine cache, JJWT 0.12, SpringDoc, Prometheus Actuator, TOTP (aerogear).

2. Application classes:
   - `AthenaJavaServiceApplication.java`: @EnableFeignClients, @EnableAsync
   - `SecurityConfig.java`: stateless JWT (no sessions), permit /api/auth/**, /actuator/, /swagger-ui/**
   - `JwtAuthenticationFilter.java`: extract Bearer token, populate SecurityContext with roles
   - `GlobalExceptionHandler.java`: handlers for BadCredentials(401), AccessDenied(403),
     MethodArgumentNotValid(400), general Exception(500)

3. `JwtUtil.java`: HS256 JJWT wrapper — extractUsername, extractRoles, extractCustomerId,
   generateToken(username, roles, customerId), isTokenValid.

4. `application.yml`: all config with ${ENV_VAR:default} substitution for postgres, rabbitmq,
   JPA (ddl-auto: validate), Caffeine (credit_scores TTL=1h, credit_reports TTL=30m), JWT, Mifos,
   CRB API URLs, champion-challenger pct, Prometheus scrape, SpringDoc.
```

---

## Prompt 9 — Java Core Business Logic

```
Implement the core Java business logic:

1. `routing/ChampionChallengerRouter.java`:
   - `@Value("${champion.challenger.pct:0.1}") double challengerPct`
   - `route()`: returns CHAMPION or CHALLENGER based on Math.random()
   - `updateChallengerPct(double pct)`: clamp to [0.0, 1.0], update field
   - `getChallengerPct()`: getter for config endpoint

2. `client/MifosClient.java`: @FeignClient pointing to `${mifos.base.url}`:
   - `getTransactions(Long clientId)` → List<MifosTransactionResponse>
   - `getClientDetails(Long clientId)` → Map
   - `getLoanAccounts(Long clientId)` → Map

3. `client/CrbApiClient.java`: WebClient-based:
   - `fetchTransUnionReport(String nationalId)` → Mono<Map>
   - `fetchMetropolReport(String nationalId)` → Mono<Map>
   Both use exponential backoff retry (3 attempts, 1s → 2s → 4s). 
   On 500, throw RuntimeException with bureau name in message.

4. `config/AthenaRabbitMQConfig.java`: Direct exchange + 3 queues:
   scoring.queue, notification.queue, dispute.queue, all with DLQ.
```

---

## Prompt 10 — Java Controllers

```
Implement all Java REST controllers:

1. `AuthController.java`: POST /api/auth/admin/login (AuthenticationManager + TOTP optional),
   POST /api/auth/customer/request-otp (OTP generation + SMS publish to RabbitMQ),
   POST /api/auth/customer/verify-otp (validate OTP code → JWT with CUSTOMER role + customerId).

2. `CrbController.java`: POST /api/v1/crb/fetch (fetch from TransUnion + Metropol reactively,
   apply ChampionChallengerRouter, forward to Python scoring service),
   GET/PUT /api/v1/crb/routing-config (show/update challengerPct, ADMIN/ANALYST only).

3. `CreditQueryController.java`: @Cacheable credit_scores (1h TTL):
   GET /api/v1/credit/score/{id}, GET /api/v1/credit/report/{id},
   POST /api/v1/credit/score/{id}/trigger (bypass cache, ADMIN/ANALYST only),
   GET /api/v1/credit/score/{id}/history?months=12.

4. `CustomerProfileController.java`: CRUD + dispute filing (publish to notification queue)
   + consent grant (generate UUID token, publish event).

5. `ThirdPartyGatewayController.java`: Consent token validation,
   GET /api/v3p/credit-score/{id}?consentToken=..., POST /api/v3p/webhooks,
   DELETE /api/v3p/consent/{id}. Every request publishes to audit log via RabbitMQ.
```

---

## Prompt 11 — Unit Tests

```
Write comprehensive unit/integration tests:

Python (pytest):
- `tests/test_scoring.py`: TestBaseScorer (5), TestCrbExtractor (5), TestPDOTransformer (6)
- `tests/test_cleansing.py`: TestSectorMapper (10), TestTargetEncoder (6)
- `tests/test_performance_mlflow.py`:
  TestNoData (2), TestDelinquencyStreaks (3), TestRollingRates (2),
  TestLoanSpacing (3), TestPaymentBehaviour (3), TestMlflowClientCompare (5)

Target: 50 tests all passing with `python3 -m pytest tests/ -v`.

Java (JUnit 5 + Mockito + MockMvc):
- `JwtUtilTest.java`: 9 tests (generation: username, roles, customerId; validation: valid, wrong user, expired, tampered)
- `ChampionChallengerRouterTest.java`: 7 tests (0%/100% deterministic, ~50% distribution 1000 samples, runtime update, clamping)
- `AuthControllerTest.java`: 6 tests (MockMvc: admin login success/failure/validation, OTP request/verify/wrong)
- `CrbApiClientTest.java`: 4 tests (MockWebServer: TransUnion success, Metropol success, 500 error, request body check)
- `GlobalExceptionHandlerTest.java`: 6 tests (status codes + error body fields for each exception type)

Add okhttp3:mockwebserver:4.12.0 to pom.xml test scope.
```

---

## Prompt 12 — Documentation & Configuration

```
Write final project documentation and configuration:

1. `monitoring/prometheus.yml`: Scrape all services: python-service:8001/metrics,
   java-service:8080/actuator/prometheus, postgres-exporter:9187, rabbitmq:15692.

2. `monitoring/alerting_rules.yml`:
   - ModelDriftKS: ks < 0.20 for 30m → warning
   - ModelDriftPSI: psi > 0.20 for 15m → critical
   - HighDefaultRate: default_rate_30d > 0.15 for 1h → warning
   - LowApprovalRate: approval_rate_30d < 0.30 for 1h → warning
   - HighScoringLatency: p95 > 5s for 10m → critical

3. `kong/kong.yml`: Routes for /api/v1/** (JWT auth, 100 req/min),
   /api/v3p/** (key-auth, 1000 req/hr), /api/v1/credit-reports (key-auth, 1000 req/hr).
   File logging for audit trail.

4. `monitoring/grafana/athena_dashboard.json`: Import-ready Grafana dashboard with:
   - KS gauge, PSI gauge, default rate gauge, approval rate gauge
   - Scoring RPS time series, latency p50/p90/p99 time series
   - Score distribution histogram, PD distribution histogram
   - Missing data rates stat, open disputes stat

5. `DEPLOYMENT.md`: prerequisites table, docker-compose up, health check commands,
   Grafana dashboard import steps, smoke test curl command, admin login, champion-challenger config,
   test commands, production hardening checklist, MLflow model registration walkthrough.

6. `docs/whitepaper.md`: Sections 5 (scoring methodology), 6 (ML pipeline),
   7 (API architecture), 9 (consent framework), 14 (monitoring).
```
