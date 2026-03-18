# Athena Credit Initiative — CLAUDE.md
> Continuity file for AI coding agents. Keep this updated as the project evolves.

---

## Project Summary

AI-powered credit scoring platform for African SMEs and individuals.
- **Score range:** 300–850 (PDO-calibrated, industry standard)
- **Scoring engine:** LightGBM (ML) + rule-based scorecard + LLM qualitative overlay
- **Target:** Kenyan market (TransUnion + Metropol CRBs, KES amounts, Africa/Nairobi timezone)

---

## Architecture

```
Kong Gateway (:80)
  ├── /api/auth/**              → user-service:8081
  ├── /api/v1/customers/**      → customer-service:8082
  ├── /api/v1/disputes/**       → customer-service:8082
  ├── /api/v1/media/**          → media-service:8083
  ├── /api/v1/credit/**         → scoring-service:8080
  ├── /api/v1/crb/**            → scoring-service:8080
  ├── /api/v1/dashboard/**      → scoring-service:8080
  ├── /api/v1/credit-score/**   → athena-python-service:8001
  ├── /api/v1/credit-report/**  → athena-python-service:8001
  ├── /api/v1/credit-reports    → athena-python-service:8001 (key-auth)
  └── /api/v3p/**               → scoring-service:8080 (key-auth)

discovery-server:8761      Eureka service registry (Spring Cloud) — kept for LMS Java services compatibility; Go services do not register
user-service:8081          Go (Gin + GORM) — admin login, customer OTP, demo-token JWT, user/role/group management
customer-service:8082      Go (Gin + GORM) — customer CRUD, maker-checker, disputes, consent
media-service:8083         Go (Gin + GORM) — file upload/download, go-cache (10 min TTL)
notification-service:8085  Go (Gin + GORM) — RabbitMQ consumer (scoring/dispute/consent events)
scoring-service:8080       Go (Gin + GORM) — CRB, credit proxy, dashboard, third-party gateway, go-cache (1h TTL)
athena-python-service:8001 FastAPI — scoring engine, MLflow, MCP server
postgres:5432              27-table schema (see Database section)
rabbitmq:5672              Async events: scoring, notifications, disputes, audit
mlflow:5000                Model registry + experiment tracking
prometheus:9090            Metrics scrape (Go services + python + infra)
grafana:3000               Dashboards (uid: athena-ops-v2)
athena-portal:5173         React (Lovable) — unified admin + client portal, shadcn/ui + Tailwind + TypeScript
```

> **Note:** Kong JWT plugin has been removed. All Go services handle JWT validation internally via the shared `pkg/athena/jwt` package.

---

## Running the Stack

```bash
cd /home/adira/AthenaCreditScore

# Start everything
docker compose up -d

# Check health (Go services use /health, not /actuator/health)
curl http://localhost:8761/actuator/health   # Eureka (discovery-server, still Java)
curl http://localhost:8081/health             # user-service (Go)
curl http://localhost:8082/health             # customer-service (Go)
curl http://localhost:8083/health             # media-service (Go)
curl http://localhost:8085/health             # notification-service (Go)
curl http://localhost:8080/health             # scoring-service (Go)
curl http://localhost:8001/health             # Python
curl http://localhost:5000/health             # MLflow

# Rebuild a Go service after code change (build context is repo root)
docker compose build user-service && docker compose up -d user-service
docker compose build scoring-service && docker compose up -d scoring-service
docker compose build athena-python-service && docker compose up -d athena-python-service

# Portal development
cd athena-portal && npm run dev   # starts on :5173

# View logs
docker logs user-service         --tail=50
docker logs scoring-service      --tail=50
docker logs athena-python-service --tail=50
```

### Quick Admin Login
```bash
curl -s -X POST http://localhost:8080/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
# Returns: {"token":"eyJ...","roles":["ADMIN"]}
```

---

## Key File Map

### Shared Go Module (`pkg/athena/`)
| Package | Purpose |
|---|---|
| `jwt/` | HS256 JWT — **base64-decodes** `JWT_SECRET` env var before use (matches Python) |
| `middleware/` | Gin middleware: JWT auth, CORS, request logging |
| `rabbitmq/` | RabbitMQ connection, exchange/queue setup, publisher/consumer helpers |
| `config/` | Shared config loading from environment |
| `database/` | GORM PostgreSQL connection with retry logic |
| `errors/` | Standardized error responses |
| `health/` | Health check endpoint handler |

### Go Microservices

#### `discovery-server/`
Eureka service registry (still Java/Spring Cloud) — kept for LMS Java services compatibility. Go services do not register with Eureka.

#### `user-service/` (port 8081)
| Path | Purpose |
|---|---|
| `cmd/main.go` | Entry point, Gin router setup, middleware registration |
| `internal/handler/` | Auth (admin login, customer OTP, demo-token), user management, groups, roles, password policy, invitations |
| `internal/model/` | GORM models: AdminUser, User, Role, Group, Invitation, PasswordPolicy |
| `internal/service/` | AuthService (DB auth, JWT generation), PasswordPolicyService |
| `internal/repository/` | GORM repositories for all models |
| `internal/seed/` | Seeds roles, groups, default admin, password policy on startup |
| `internal/dto/` | Request/response DTOs |

#### `customer-service/` (port 8082)
| Path | Purpose |
|---|---|
| `cmd/main.go` | Entry point, Gin router setup |
| `internal/handler/` | Customer CRUD, paginated list, maker-checker approve/reject, CSV whitelist, disputes, consent, identity-document, admin dispute list |
| `internal/client/` | HTTP client to media-service for document validation |
| `internal/dto/` | CustomerRequest, MediaResponse, PageResponse DTOs |

#### `media-service/` (port 8083)
| Path | Purpose |
|---|---|
| `cmd/main.go` | Entry point, Gin router setup |
| `internal/handler/` | File upload/download, search, stats endpoints |
| `internal/model/` | GORM model: Media (referenceId, tags, isPublic, thumbnail) |
| `internal/repository/` | GORM repository with advanced queries |
| `internal/service/` | Disk I/O, path traversal protection, go-cache (10 min TTL) |
| `internal/config/` | Service-specific configuration |

#### `notification-service/` (port 8085)
| Path | Purpose |
|---|---|
| `cmd/main.go` | Entry point, Gin router setup, RabbitMQ consumer startup |
| `internal/handler/` | Notification config CRUD, manual send endpoint |
| `internal/listener/` | Consumes `athena.notification.queue` and `athena.dispute.queue` (DISPUTE_FILED, SCORE_UPDATED, CONSENT_GRANTED, USER_INVITATION) |
| `internal/model/` | GORM models: NotificationConfig, NotificationLog |
| `internal/repository/` | GORM repositories for config and logs |
| `internal/service/` | Email sending (SMTP from DB config), Athena templates, audit logging |
| `internal/seed/` | Seeds default EMAIL and SMS configs (disabled by default) |

#### `scoring-service/` (port 8080)
| Path | Purpose |
|---|---|
| `cmd/main.go` | Entry point, Gin router setup |
| `internal/handler/` | 9 handlers: CreditQuery, Dashboard, Crb, ThirdPartyGateway, Auth, CustomerProfile, and more |
| `internal/client/` | HTTP clients to Python scoring engine, CRB APIs |
| `internal/routing/` | Champion-challenger traffic split, runtime-updatable |
| `internal/cache/` | go-cache: credit scores and reports (TTL = 1 hour) |
| `internal/model/` | GORM models for routing config, audit log, champion-challenger log |
| `internal/dto/` | Request/response DTOs |

> Note: scoring-service also contains Auth and CustomerProfile handlers
> for backwards-compat with the portal proxy (which points to :8080).

### Python Service (`athena-python-service/`)
| File | Purpose |
|---|---|
| `main.py` | FastAPI app, lifespan, CORS, rate limiting |
| `auth/jwt_handler.py` | JWT verify — **base64-decodes** `JWT_SECRET` to match Java |
| `scoring/base_scorer.py` | 5-dimension scorecard (income stability, level, savings, low-balance, diversity) → 300–700 |
| `scoring/crb_extractor.py` | Bureau score normalisation, NPA penalty, active default flag → [−100,+150] |
| `scoring/pdo_transformer.py` | PD → PDO credit score (300–850), inverse function |
| `scoring/hybrid_scorer.py` | Orchestrator: base + CRB + LLM → PD → PDO |
| `scoring/lgbm_scorer.py` | LightGBM champion/challenger inference from MLflow |
| `llm/client.py` | Dual-mode: OpenAI or local Ollama/vLLM (same `openai` package, different `base_url`) |
| `llm/prompts.py` | Credit analyst prompt → `{"adjustment": int, "reasoning": str}` |
| `api/credit_reports.py` | Inbound CRB report → score → persist to DB |
| `api/scoring.py` | `GET /api/v1/credit-score/{customer_id}`, `GET /api/v1/credit-report/{customer_id}` |
| `mlops/trainer.py` | LightGBM train + SHAP + metrics → MLflow registry |
| `feedback/loop.py` | Weekly APScheduler: KS/PSI drift → auto-retrain |
| `mcp_server.py` | MCP server with 7 tools for AI agent workflows |
| `monitoring/metrics.py` | Prometheus counters, histograms, PSI/KS gauges |

### Portal (`athena-portal/`, port 5173)

Unified portal built with Lovable -- shadcn/ui + Radix + Tailwind CSS + TypeScript + @tanstack/react-query.

Landing page at `/` with links to admin and client portals.

| Section | Pages |
|---|---|
| Admin | Dashboard, CustomerSearch, Disputes, ModelConfig, AuditLogs, UserManagement, NotificationManagement, Analytics, NPL, Reports, SystemConfig |
| Client | CreditDashboard, CreditReport (with LLM reasoning), Disputes, ConsentManagement, ScoreSimulator, BureauComparison, Alerts, CreditFreeze, Education, Settings |

Portal proxies `/api/**` to Go services via Kong Gateway.

---

## Database (PostgreSQL `athena_db`)

27 tables total. Key ones:

| Table | Purpose |
|---|---|
| `customers` | 1000 seeded customers with `customer_id`, `national_id`, `mobile_number` |
| `credit_score_events` | 1533 scoring events — `final_score`, `pd_probability`, `scored_at` |
| `loans` | Loan records with `status` ('DEFAULT', 'ACTIVE', 'CLOSED') |
| `repayments` | Repayment history — `amount_paid`, `penalty_amount` |
| `disputes` | Customer disputes — `status` ('OPEN', 'RESOLVED', 'CLOSED'), `reason` |
| `consents` | Partner consent tokens — `scope`, `expires_at`, `revoked_at` |
| `audit_log` | Third-party access log |
| `champion_challenger_log` | Per-request model routing log |
| `routing_config` | Live challenger traffic % |
| `admin_users` | Admin accounts (default: `admin`/`admin`) |
| `base_score_breakdowns` | Per-dimension score contributions |

---

## API Endpoints Reference

### Auth
```
POST /api/auth/admin/login              → JWT (roles: ADMIN)
POST /api/auth/customer/request-otp    → SMS OTP sent
POST /api/auth/customer/verify-otp     → JWT (roles: CUSTOMER, customerId claim)
```

### Credit (Java proxies to Python)
```
GET  /api/v1/credit/score/{customerId}          → cached credit score
GET  /api/v1/credit/report/{customerId}         → full report + DB metrics
POST /api/v1/credit/score/{customerId}/trigger  → fresh scoring run
GET  /api/v1/credit/score/{customerId}/history  → score history (stub, wires to credit_score_events)
```

### Python Direct (X-Api-Key: dev-key OR Bearer JWT)
```
POST /api/v1/credit-reports             → ingest CRB report → score → persist
GET  /api/v1/credit-score/{customer_id} → latest score from DB
GET  /api/v1/credit-report/{customer_id}→ full score breakdown
```

### Customers / Disputes
```
GET  /api/v1/customers                      → paginated list (page, size params)
GET  /api/v1/customers/search?q=            → search by name/phone/id
POST /api/v1/customers                      → create customer (PENDING, requires checker approval)
GET  /api/v1/customers/{id}                 → profile with score join ✅
PUT  /api/v1/customers/{id}                 → update profile
PUT  /api/v1/customers/{id}/approve         → maker-checker approve (ADMIN/ANALYST, not same as creator)
PUT  /api/v1/customers/{id}/reject          → maker-checker reject (ADMIN/ANALYST, not same as creator)
PUT  /api/v1/customers/{id}/identity-document?documentId= → link doc (validates via media-service)
GET  /api/v1/customers/{id}/disputes        → disputes for one customer ✅
POST /api/v1/customers/{id}/disputes        → file new dispute (→ RabbitMQ notification)
PUT  /api/v1/customers/{id}/consent         → grant partner consent (persists to consents table ✅)
POST /api/v1/customers/whitelist            → CSV bulk whitelist upload (auto-APPROVED)
GET  /api/v1/disputes                       → admin list all disputes (filterable by status)
PUT  /api/v1/disputes/{id}                  → update dispute status
```

### Dashboard / Model
```
GET  /api/v1/dashboard/stats            → KS, PSI, approval rate, avg score, open disputes
GET  /api/v1/crb/routing-config         → current challenger %
PUT  /api/v1/crb/routing-config?challengerPct=0.2 → update split at runtime
```

---

## Critical Technical Notes

### JWT Secret — MUST READ
- `JWT_SECRET` in `.env` is a **base64-encoded** string.
- **Go** (`pkg/athena/jwt/`): `base64.StdEncoding.Decode` before use — all 5 Go services share this package.
- **Python** (`auth/jwt_handler.py`): `base64.b64decode(_raw_secret)` — also decodes before use.
- Both Go and Python services use identical raw key bytes. Never change one without the other.
- Kong JWT plugin has been removed — services handle JWT validation internally.

### LLM Mode
- `LLM_PROVIDER=openai` → uses `OPENAI_API_KEY` and `LLM_MODEL` (default: `gpt-4o-mini`)
- `LLM_PROVIDER=local` → points `base_url` to Ollama or vLLM endpoint, zero code change
  - For Ollama: set `LLM_BASE_URL=http://<host>:11434/v1` and `LLM_MODEL=qwen2.5-coder:7b`
  - Ollama must listen on all interfaces: `OLLAMA_HOST=0.0.0.0`
- When `OPENAI_API_KEY` is not set, LLM adjustment returns 0 and `"LLM analysis unavailable."`

### Champion-Challenger
- Default: `CHALLENGER_TRAFFIC_PCT=0.0` (all traffic to champion)
- Update live: `PUT /api/v1/crb/routing-config?challengerPct=0.2`
- Every request logged to `champion_challenger_log`

### Caffeine Cache
- `credit_scores` cache: TTL = 1 hour
- `credit_reports` cache: TTL = 1 hour
- Bypass by calling Python service directly or using the trigger endpoint

---

## Test Coverage

### Python (pytest) — 50 tests
```bash
cd athena-python-service
pip install -r requirements.txt
pytest tests/ -v --tb=short
```
| Class | Tests |
|---|---|
| TestBaseScorer | 5 |
| TestCrbExtractor | 5 |
| TestPDOTransformer | 6 |
| TestSectorMapper | 10 |
| TestTargetEncoder | 6 |
| TestNoData / TestDelinquencyStreaks / TestRollingRates / TestLoanSpacing / TestPaymentBehaviour | 12 |
| TestMlflowClientCompare | 5 |

### Java (JUnit 5) — 32 tests
```bash
cd athena-java-service && mvn test
```
| Class | Tests |
|---|---|
| JwtUtilTest | 9 |
| ChampionChallengerRouterTest | 7 |
| AuthControllerTest | 6 |
| CrbApiClientTest | 4 |
| GlobalExceptionHandlerTest | 6 |

### Load Test
```bash
cd /home/adira/AthenaCreditScore
python3 simulate_app_traffic.py
# 200 customers, 15 concurrent threads, 400 API interactions, 0 failures
```

---

## Known Issues Fixed (Feb 2026)

| Issue | Root Cause | Fix |
|---|---|---|
| `GET /api/v1/credit/report/{id}` → 500 | Python JWT validation failed — Java encodes with base64-decoded bytes, Python used raw string | `auth/jwt_handler.py`: `base64.b64decode(JWT_SECRET)` |
| `GET /api/v1/customers/{id}/disputes` → empty stub | `CustomerProfileController.getDisputes` returned hardcoded empty list | Wired to `disputes` table via `jdbcTemplate.queryForList` |
| `GET /api/v1/credit-score?customerId=1` → 404 | Wrong URL format — endpoint is path param, not query param | Use `/api/v1/credit-score/{customer_id}` |

## Microservice Porting (Feb 2026 — from athena-device-finance)

All 4 services ported and enhanced:

| Service | What Was Added |
|---|---|
| `media-service` | Extended Media model (referenceId, tags, isPublic, thumbnail), advanced repo queries, general upload overload, search, stats, GlobalExceptionHandler, WebConfig, OpenApiConfig, V2 migration |
| `notification-service` | DB-backed config (SMTP + SMS), NotificationLog audit table, NotificationService (JavaMailSenderImpl from DB), 3 template methods, NotificationController, USER_INVITATION event handler, V1 migration |
| `user-service` | Full user management: User/Role/Group/Invitation/PasswordPolicy JPA entities, 5 repos, AuthService, PasswordPolicyService, DataInitializer, 5 controllers (users, groups, roles, policy, invitations), AOP LoggingAspect, invitation email via RabbitMQ, V1 migration (flyway) |
| `customer-service` | Paginated list, create (PENDING), maker-checker approve/reject, CSV whitelist upload, identity-document linking via Feign→media-service, GlobalExceptionHandler, OpenApiConfig, WebConfig, Flyway V1 (adds created_by/approved_by/approved_at/rejection_reason/identity_document_id) |

---

## Outstanding / Next Steps

### Phase 8 — Documentation
- [ ] Finalize `docs/whitepaper.md` (sections 1–4, 8, 10–13 not yet written)
- [ ] Finalize `docs/build_prompts.md`

### Stubs to Wire
- [x] `GET /api/v1/credit/score/{customerId}/history` — wired to `credit_score_events` ✅
- [x] `GET /api/v1/customers/{customerId}` — wired to `customers` + `credit_score_events` join ✅
- [x] Consent persistence — persists to `consents` table ✅

### Minor Linting
- [ ] CSS compatibility warnings in admin/client portal builds
- [x] Java type-safety warnings (raw `Map` types in `CreditQueryController`) — fixed with `ParameterizedTypeReference<Map<String,Object>>` ✅

### Features Not Yet Built
- [ ] Score history chart in admin `CustomerSearchPage` slide-in panel (data endpoint exists as stub)
- [ ] Data deletion flow (GDPR/DPA — marked as "future automation" in whitepaper §9.3)
- [ ] TOTP second factor for admin login (configurable per-admin, not yet enforced in `AuthController`)

---

## Monitoring URLs

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3000 | admin / admin_change_me |
| Prometheus | http://localhost:9090 | — |
| MLflow | http://localhost:5000 | — |
| RabbitMQ Management | http://localhost:15672 | athena / athena_secret_change_me |
| Kong Admin | http://localhost:8444 | — |
| Admin Portal | http://localhost:5173 | admin / admin |
| Client Portal | http://localhost:5174 | OTP via phone |

---

## Environment Variables (`.env`)

Critical ones to set before first run:
```
JWT_SECRET=<openssl rand -base64 32>
OPENAI_API_KEY=sk-...          # or set LLM_PROVIDER=local
MIFOS_BASE_URL=...             # core banking integration
TRANSUNION_API_KEY=...
METROPOL_API_KEY=...
GRAFANA_PASSWORD=...
```

---

## Code Reuse Provenance

| Component | Source | Change |
|---|---|---|
| `JwtUtil.java` | `athena-device-finance/user-service` | +`extractRoles`, `extractCustomerId` |
| `AthenaRabbitMQConfig.java` | `user-service` RabbitMQConfig | 3 queues instead of 1 |
| `AuthController.java` | `user-service` | +OTP customer flow |
| Feign client pattern | `customer-service` UserClient | → `MifosClient`, `CrbApiClient` |
| Caffeine cache config | `media-service` CacheConfig | Verbatim |
| Notification via RabbitMQ | `notification-service` InvitationEventListener | → `ScoringEventListener` |
