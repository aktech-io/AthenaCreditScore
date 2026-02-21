# Athena Credit Initiative

**AI-powered credit scoring for African SMEs and individuals — built on LightGBM, GPT/Ollama, and MLflow.**

---

## Architecture

```
Kong Gateway (:80)
    ├── /api/auth           → athena-java-service:8080
    ├── /api/v1/crb         → athena-java-service:8080 (champion-challenger → python)
    ├── /api/v1/credit-*    → athena-python-service:8001
    └── /api/v1/credit-reports → athena-python-service:8001 (API-key secured)

athena-python-service:8001  — FastAPI + MCP, scoring engine, MLflow integration
athena-java-service:8080    — Spring Boot, CRB/Mifos clients, auth, RabbitMQ pub
postgres:5432               — 23-table schema (core + MLOps + feature store + portal)
rabbitmq:5672               — messaging for scoring triggers and notifications
mlflow:5000                 — model registry and experiment tracking
prometheus:9090 + grafana:3000 — metrics and alerting
```

---

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — set JWT_SECRET, OPENAI_API_KEY (or LLM_PROVIDER=local), DB passwords

# 2. Start all services
docker-compose up -d

# 3. Initialise the database (schema applied automatically via Docker entrypoint)
docker-compose logs postgres | grep "database system is ready"

# 4. Verify health
curl http://localhost:80/health                          # Kong gateway
curl http://localhost:8001/health                       # Python service
curl http://localhost:8080/actuator/health              # Java service
curl http://localhost:5000/health                       # MLflow

# 5. Run smoke test
curl -X POST http://localhost:8001/api/v1/credit-reports \
     -H "X-Api-Key: dev-key" \
     -H "Content-Type: application/json" \
     -d @athena-python-service/tests/fixtures/sample_crb_report.json
```

---

## LLM Configuration

| Mode | Config |
|---|---|
| **OpenAI (default)** | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=sk-...` |
| **Local (Ollama)** | `LLM_PROVIDER=local`, `LLM_BASE_URL=http://ollama:11434/v1`, `LLM_MODEL=llama3:70b` |
| **Local (vLLM)** | `LLM_PROVIDER=local`, `LLM_BASE_URL=http://vllm:8000/v1`, `LLM_MODEL=mistral-7b` |

Zero code changes required to switch modes — just update `.env` and restart the Python service.

---

## Champion-Challenger Routing

Set `CHALLENGER_TRAFFIC_PCT=0.2` in `.env` to route 20% of scoring traffic to the challenger model.

View/update routing config at runtime:
```bash
# View
curl http://localhost:8080/api/v1/crb/routing-config

# Update (admin)
curl -X PUT "http://localhost:8080/api/v1/crb/routing-config?challengerPct=0.3" \
     -H "Authorization: Bearer <admin-token>"
```

---

## Running Tests

```bash
cd athena-python-service
pip install -r requirements.txt
pytest tests/ -v --tb=short
# 16 tests: BaseScorer (5), CrbExtractor (5), PDOTransformer (6)
```

---

## Monitoring

| Dashboard | URL |
|---|---|
| Grafana | http://localhost:3000 (admin/admin_change_me) |
| Prometheus | http://localhost:9090 |
| MLflow | http://localhost:5000 |
| RabbitMQ Management | http://localhost:15672 |

---

## Service Provenance (Reused Code)

| Component | Reused From |
|---|---|
| `JwtUtil.java` | `user-service` — verbatim HS256 JWT utility |
| `AthenaRabbitMQConfig.java` | `user-service` RabbitMQConfig — adapted with 3 queues |
| `CrbApiClient.java` | Feign client pattern from `customer-service` UserClient |
| `AuthController.java` | `user-service` AuthService/AuthController — extended for OTP |
| Caffeine cache | `media-service` CacheConfig — identical pattern |
| Notification via RabbitMQ | `notification-service` InvitationEventListener — same pattern |

---

## Score Interpretation

| Score Range | Band | Typical Approval |
|---|---|---|
| 780 – 850 | Excellent | Auto-approve |
| 720 – 779 | Very Good | Approve |
| 680 – 719 | Good | Approve with standard terms |
| 640 – 679 | Fair | Manual review |
| 600 – 639 | Marginal | Conditional / reduced limit |
| 300 – 599 | Poor | Decline / escalate |
