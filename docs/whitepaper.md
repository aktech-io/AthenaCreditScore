# Athena Credit Initiative — Technical Whitepaper
## Enhanced Sections: 5, 6, 7, 9, 14

---

## Section 5: Credit Scoring Methodology

### 5.1 Hybrid Scoring Architecture

The Athena scoring engine employs a three-layer hybrid approach that combines:

1. **Quantitative Base Score** (transactional signals, 300–700 range)
2. **CRB Signal** (bureau score normalisation + NPA/default history, −100 to +150 pts)
3. **LLM Qualitative Adjustment** (±50 pts narrative overlay from business context)

These three signals are blended into a composite **Probability of Default (PD)** estimate, which is then transformed into an industry-standard **300–850 PDO credit score** via a calibrated log-odds transformation.

### 5.2 Quantitative Base Scorer

Five scorecard dimensions contribute to the base score:

| Dimension | Max Points | Signal |
|---|---|---|
| Income Stability | 120 | Coefficient of variation of monthly inflows |
| Income Level | 100 | Median monthly net flow vs. national thresholds |
| Savings Rate | 80 | (Inflows − Outflows) / Inflows |
| Low-Balance Events | 100 | Frequency of balance < KES 500 |
| Transaction Diversity | 100 | Number of distinct counter-party categories |

All contributions are linearly scaled and clamped to their dimension maxima. The total (300–700) serves as the entry-point composite before CRB enrichment.

### 5.3 CRB Metrics Extraction

Credit Reference Bureau data (TransUnion + Metropol) provides:
- **Bureau Score** (0–900): normalised to 0–90 point contribution
- **NPA Count**: −15 pts each (min 0, max penalty = 3 NPAs)
- **Active Default Flag**: −40 pts if any current default exists

The CRB contribution is hard-clamped to [−100, +150].

### 5.4 LLM Adjustment Layer

A structured credit-analyst prompt is sent to the language model (OpenAI GPT-4o or local Llama 3.1-70B). The prompt includes:
- Application-time features (capital growth ratio, revenue per employee, profit margin)
- Sector density context
- Historical CRB summary

The model returns a JSON payload: `{"adjustment": -20, "reasoning": "..."}`. Adjustments outside ±50 pts are clipped.

### 5.5 PDO Transformation

**Points-to-Double-Odds (PDO)** calibration maps probability of default to a standardised credit score:

```
score = base_score − (PDO / ln(2)) × ln(pd / (1 − pd) / base_odds)
```

Default calibration parameters:
- `BASE_SCORE = 500` (PD = 50% maps to score 500)
- `BASE_ODDS = 1.0` (even odds at centre)
- `PDO = 50` (every 50-point increase halves odds of default)

Final scores are clamped to [300, 850].

### 5.6 Score Bands

| Band | Score Range | Interpretation |
|---|---|---|
| Prime | 720–850 | Very low risk, standard pricing |
| Near-Prime | 630–719 | Low risk, minor premium |
| Subprime | 500–629 | Moderate risk, risk-adjusted pricing |
| Marginal | 400–499 | High risk, requires collateral |
| Decline | 300–399 | Adverse history, manual review required |

---

## Section 6: Machine Learning Pipeline

### 6.1 Feature Engineering

Features are categorised into three groups:

**Application Features** (computed at loan application time):
- `capital_growth_ratio`: (current_capital − initial_capital) / initial_capital
- `revenue_per_employee`: annual_revenue / employee_count
- `profit_margin`: net_profit / gross_revenue
- `sector_density`: fraction of loans in the same sector within the same region

**Performance Features** (computed from historical loan behaviour):
- `max_delinquency_streak`: longest consecutive late-payment months
- `current_delinquency_streak`: trailing late payments
- `delinquency_rate_90d`: fraction of payments late within 90 days
- `payment_cv`: coefficient of variation of payment amounts (regularity signal)
- `avg_loan_spacing_days`: mean days between loan disbursements
- `early_repayment_rate`: fraction of payments made before due date
- `partial_payment_rate`: fraction of payments below 95% of due amount

**Categorical Encodings**:
- Sector (12 levels) → target-encoded with 5-fold CV + smoothing (α = 10)
- Region/County (47 levels) → same methodology
- Encoding maps stored as JSON in `feature_definitions.encoding_config`

### 6.2 LightGBM Model

The challenger model is trained on:
- **Objective**: binary cross-entropy
- **Positive label**: loan defaulted within 12 months
- **Validation**: stratified 5-fold cross-validation
- **Evaluation metrics**: AUC-ROC, KS statistic, PR-AUC

Key hyperparameters (tuned via Optuna):

```python
{
    "num_leaves": 63,
    "min_child_samples": 50,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
}
```

SHAP values are logged per feature at training time and re-computed weekly on recent defaults via the `shap_analyzer`.

### 6.3 MLOps Lifecycle

```
New data → Feature engineering → Training run (MLflow)
         → Staging alias → Human review → Challenger alias
         → A/B traffic split (ChampionChallengerRouter)
         → Weekly comparison (compare_champion_challenger)
         → Auto-promotion if KS ≥ +0.02 or AUC ≥ +0.005
         → Rollback if KS ≤ −0.03 or AUC ≤ −0.01
```

---

## Section 7: API Architecture

### 7.1 Service Topology

```
Client / Admin Portal
       │
       ▼
Kong API Gateway (80)
  ├── JWT auth (portal routes)
  ├── API key auth (external /api/v3p)
  └── Rate limiting (100 req/min portal, 1000 req/hr external)
       │
       ├── athena-java-service:8080
       │     ├── /api/auth/**         AuthController
       │     ├── /api/v1/crb/**       CrbController (orchestration)
       │     ├── /api/v1/credit/**    CreditQueryController (cached proxy)
       │     ├── /api/v1/customers/** CustomerProfileController (CRUD + disputes)
       │     └── /api/v3p/**          ThirdPartyGatewayController (consent + audit)
       │
       └── athena-python-service:8001
             ├── /api/v1/credit-reports  Inbound CRB ingest + scoring
             ├── /api/v1/credit-score    Score lookup
             └── /api/v1/credit-report   Full report with breakdown
```

### 7.2 Authentication Flows

**Admin Login:**
1. `POST /api/auth/admin/login` → Spring Security authenticates against `admin_users`
2. TOTP second factor (optional, configurable per admin)
3. Returns JWT (HS256, 24h TTL) with roles claim

**Customer OTP:**
1. `POST /api/auth/customer/request-otp?phone=+254...` → SMS OTP sent
2. `POST /api/auth/customer/verify-otp?phone=...&otp=...` → JWT issued with `CUSTOMER` role and `customerId` claim

**Third-Party Access:**
1. Partner includes `X-Api-Key` header (validated by Kong key-auth plugin)
2. Partner includes `?consentToken=...` (validated by `ThirdPartyGatewayController`)
3. Every request publishes an audit log event to RabbitMQ

---

## Section 9: Data Privacy and Consent Framework

### 9.1 Consent Model

Consent is customer-scoped and partner-scoped:

```sql
consents (
  consent_id, customer_id, partner_id,
  scope,          -- 'CREDIT_SCORE' | 'FULL_REPORT' | 'TRANSACTION_DATA'
  consent_token,  -- UUID, passed by partner in API requests
  granted_at, expires_at, revoked_at
)
```

A consent token is valid only if:
- `revoked_at IS NULL`
- `expires_at > NOW()`
- `scope` includes the requested data type

### 9.2 Audit Trail

All third-party data access events are published to RabbitMQ → consumed by an audit consumer → persisted to `audit_log`:

```sql
audit_log (
  log_id, partner_id, customer_id,
  action,    -- 'CREDIT_SCORE_REQUEST' | 'CONSENT_REVOKED' | ...
  outcome,   -- 'APPROVED' | 'DENIED_NO_CONSENT' | ...
  ip_address, timestamp
)
```

Kong additionally logs all gateway-level requests to `/var/log/kong/access.log`.

### 9.3 Customer Rights

| Right | Mechanism |
|---|---|
| View credit report | `GET /api/v1/credit/{customerId}` (CUSTOMER role) |
| File dispute | `POST /api/v1/customers/{id}/disputes` |
| Grant consent | `PUT /api/v1/customers/{id}/consent` |
| Revoke consent | `DELETE /api/v3p/consent/{customerId}` |
| Request data deletion | Manual process (GDPR/DPA compliance, future automation) |

---

## Section 14: Monitoring and Observability

### 14.1 Metrics Architecture

```
Python service → Prometheus /metrics endpoint (port 8001)
Java service  → Spring Actuator /actuator/prometheus (port 8080)
PostgreSQL    → postgres_exporter (port 9187)
RabbitMQ      → rabbitmq_exporter (port 15692)

Prometheus (9090) scrapes all → Grafana (3000) visualises
Alertmanager receives alerts → configured receivers (Slack/email)
```

### 14.2 Key Metrics

| Metric | Type | Alert Threshold |
|---|---|---|
| `athena_ks_statistic` | Gauge | < 0.20 → WARNING |
| `athena_psi_value{feature="pd_probability"}` | Gauge | > 0.20 → CRITICAL |
| `athena_default_rate_30d` | Gauge | > 0.15 → WARNING |
| `athena_approval_rate_30d` | Gauge | < 0.30 → WARNING |
| `athena_scoring_latency_p95` | Histogram | > 5s → CRITICAL |
| `athena_data_missing_rate` | Gauge | > 0.05 → WARNING |

### 14.3 Grafana Dashboard Panels

The `athena_dashboard.json` dashboard (uid: `athena-ops-v2`) contains 10 panels across 4 rows:

1. **Model Health**: KS gauge, PSI gauge, 30d Default Rate, 30d Approval Rate
2. **Scoring Operations**: Requests/sec by model target, Latency p50/p90/p99
3. **Score Distribution**: Final score histogram (by band), PD probability histogram
4. **Data Quality**: Missing data rates per field, Open disputes count

Dashboard auto-refreshes every 30 seconds. Timezone: `Africa/Nairobi`.

### 14.4 Alertmanager Rules

| Alert | Condition | Severity |
|---|---|---|
| `ModelDriftKS` | KS < 0.20 for 30min | warning |
| `ModelDriftPSI` | PSI > 0.20 for 15min | critical |
| `HighDefaultRate` | Default rate > 15% for 1hr | warning |
| `LowApprovalRate` | Approval rate < 30% for 1hr | warning |
| `HighScoringLatency` | p95 latency > 5s for 10min | critical |
| `MissingDataSpike` | Any field missing rate > 5% for 30min | warning |
