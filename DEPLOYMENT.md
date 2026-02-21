# Athena Credit Initiative — Deployment Guide

## Prerequisites

| Tool | Minimum Version |
|---|---|
| Docker | 24.0+ |
| Docker Compose | 2.24+ |
| Java (for Java service local dev) | 17 |
| Python (for Python service local dev) | 3.11+ |
| Maven (for Java builds) | 3.9+ |

---

## 1. First-Time Setup

```bash
# Clone the repo
git clone https://github.com/your-org/AthenaCreditScore.git
cd AthenaCreditScore

# Copy and configure environment variables
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
JWT_SECRET=<generate with: openssl rand -base64 64>
POSTGRES_PASSWORD=<strong password>

# LLM — choose one:
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# OR local:
# LLM_PROVIDER=local
# LLM_BASE_URL=http://ollama:11434/v1
# LLM_MODEL=llama3:70b
```

---

## 2. Start All Services

```bash
docker-compose up -d
```

This starts 8 containers:

| Container | Port | Purpose |
|---|---|---|
| `postgres` | 5432 | PostgreSQL (schema auto-applied) |
| `rabbitmq` | 5672 / 15672 | Message broker + management UI |
| `mlflow` | 5000 | Model registry + experiment tracking |
| `athena-java-service` | 8080 | Java Spring Boot API |
| `athena-python-service` | 8001 | FastAPI scoring + MCP |
| `prometheus` | 9090 | Metrics scraping |
| `grafana` | 3000 | Dashboards |
| `kong` | 80 / 8001 | API Gateway |

**Wait for readiness (~60s):**

```bash
docker-compose logs -f --tail=20 athena-python-service
# Watch for: "Application startup complete"

docker-compose logs -f --tail=20 athena-java-service
# Watch for: "Started AthenaJavaServiceApplication"
```

---

## 3. Verify Health

```bash
# Gateway
curl http://localhost:80/health

# Python service
curl http://localhost:8001/health

# Java service
curl http://localhost:8080/actuator/health

# MLflow
curl http://localhost:5000/health
```

---

## 4. Load Grafana Dashboard

1. Open Grafana: [http://localhost:3000](http://localhost:3000)
2. Login: `admin` / `admin_change_me` (set `GF_SECURITY_ADMIN_PASSWORD` in `.env`)
3. Go to **Dashboards → Import**
4. Upload: `monitoring/grafana/athena_dashboard.json`
5. Select **Prometheus** as the data source

---

## 5. Run Smoke Test

```bash
# Ingest a sample CRB report and get a score
curl -X POST http://localhost:80/api/v1/credit-reports \
     -H "X-Api-Key: dev-key" \
     -H "Content-Type: application/json" \
     -d @athena-python-service/tests/fixtures/sample_crb_report.json | jq .
```

Expected response:
```json
{
  "customer_id": 1,
  "final_score": 520,
  "score_band": "Marginal",
  "pd_probability": 0.28,
  ...
}
```

---

## 6. Admin Login

```bash
# Get admin JWT token
curl -X POST http://localhost:8080/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_admin_password"}'
```

---

## 7. Champion-Challenger Configuration

```bash
# View current split
curl http://localhost:8080/api/v1/crb/routing-config

# Route 20% of traffic to challenger model
curl -X PUT "http://localhost:8080/api/v1/crb/routing-config?challengerPct=0.2" \
     -H "Authorization: Bearer <admin-token>"
```

---

## 8. Running Unit Tests

```bash
# Python (no external services needed)
cd athena-python-service
python3 -m pytest tests/ -v
# Expected: 50 passed

# Java (requires Maven)
cd athena-java-service
mvn test
# Expected: 32 tests passed
```

---

## 9. Production Hardening Checklist

- [ ] Change all default passwords in `.env` (Postgres, RabbitMQ, Grafana)
- [ ] Set a strong `JWT_SECRET` (minimum 256-bit)
- [ ] Set `LLM_PROVIDER=openai` with a real `OPENAI_API_KEY`, or deploy Ollama alongside
- [ ] Replace `dev-key` in Kong consumer config with randomly generated production API keys
- [ ] Enable TLS: configure Kong with SSL certificates (`kong-ssl.yml`)
- [ ] Set `CRB_TRANSUNION_API_KEY` and `CRB_METROPOL_API_KEY` with real credentials
- [ ] Configure SMTP in `.env` for the notification service
- [ ] Set `MIFOS_BASE_URL`, `MIFOS_USERNAME`, `MIFOS_PASSWORD` to your Apache Fineract instance
- [ ] Set Prometheus alertmanager receiver (email/Slack) in `monitoring/alerting_rules.yml`
- [ ] Enable `CHALLENGER_TRAFFIC_PCT=0.0` initially; increase gradually after first champion model is trained

---

## 10. MLflow Model Registration

After collecting enough training data (recommended: ≥ 500 labelled loans):

```bash
# Via Python SDK
cd athena-python-service
python3 -c "
from mlops.trainer import train_and_register
import asyncio
asyncio.run(train_and_register())
"
```

This will:
1. Fetch feature vectors from PostgreSQL
2. Train LightGBM with 5-fold cross-validation
3. Log AUC, KS, SHAP values to MLflow
4. Register the model under `athena_lgbm_scorer`

Promote to champion via MLflow UI at [http://localhost:5000](http://localhost:5000) → Models → `athena_lgbm_scorer` → set alias `champion`.

---

## 11. Shutdown

```bash
docker-compose down          # Stop containers (preserve data)
docker-compose down -v       # Stop containers + delete volumes (clean slate)
```
