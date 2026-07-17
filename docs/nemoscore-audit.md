# NemoScore Product Audit — Gap Analysis & Rebuild Plan

> Audit of AthenaCreditScore (to be rebranded **NemoScore**, the credit-scoring engine of the
> Nemo neobank platform, consumed by AthenaIntelligentLMS).
> Date: 2026-07-18. Audit basis: full code review of the scoring engine, Go services, and the
> LMS integration, benchmarked against international model-risk standards (SR 11-7, Basel/IFRS 9,
> EU AI Act) and Kenyan regulation (CBK DCP Regulations 2022, CRB Regulations 2020, DPA 2019).

---

## 1. Executive Summary

The platform is an impressive **architectural** achievement (7 services, MLflow, Prometheus/Grafana,
unified portal, champion/challenger plumbing) but the **scoring core is not yet a real credit model**.
The three findings that matter most, all verified in code:

1. **The ML model is never used.** `scoring/hybrid_scorer.py` never calls `lgbm_scorer.py`.
   Every production score is rule-based scorecard + LLM tweak. The champion/challenger routing,
   MLflow registry, and `model_target` field are recorded but have zero effect on the score.
2. **The PD is fictional.** `_score_to_pd()` is a hand-tuned logistic (`k=0.012, midpoint=500`)
   with no empirical calibration to observed defaults. The PDO transform then dresses this up as
   a 300–850 score. Any pricing, provisioning (IFRS 9 ECL), or limit decision built on
   `pd_probability` is built on an invented number.
3. **The LMS silently invents scores.** `AthenaScoreClient.GetScore` in AthenaIntelligentLMS
   falls back to a **deterministic mock derived from the customer ID** whenever the scoring API
   is down, non-2xx, or un-parseable — and returns it as if real (`err == nil`). Loan decisions
   can be made on fabricated credit data with only a log line as evidence. The mock also uses a
   different band scale (A–D, 300–900) than the engine (Excellent–Poor, 300–850).

**Verdict:** usable as a demo/prototype; not yet usable for real lending. The rebuild plan
(§6) sequences the work: make the score honest → make the data real → govern the model →
ship the differentiating features.

---

## 2. Verified Code Findings (by severity)

### Critical

| # | Finding | Evidence |
|---|---------|----------|
| C1 | LightGBM/MLflow inference is dead code in the scoring path; scores are scorecard + LLM only | `hybrid_scorer.py` — no import/call of `get_lgbm_scorer`; `model_target` only stored |
| C2 | PD not calibrated to outcomes; PDO transform applied to a guessed PD | `hybrid_scorer._score_to_pd`, `pdo_transformer.py` |
| C3 | LMS mock-score fallback fabricates scores for loan decisions on any API failure | `AthenaIntelligentLMS go-services/internal/scoring/client/external.go:74` |
| C4 | LLM can move a score ±50 pts (≈ two bands) — non-deterministic, unversioned prompt, no independent validation, output not bounds-checked beyond the prompt's own instruction | `llm/prompts.py`, `hybrid_scorer.py:100` |

### High

| # | Finding | Evidence |
|---|---------|----------|
| H1 | Scorecard weights/thresholds are hard-coded guesses — no development sample, no WoE binning, no Gini/KS on real outcomes, only 5 features | `base_scorer.py` (income > KES 100k → max pts, etc.) |
| H2 | CRB contribution clamped to **[0, +150]** — negative bureau information can never push a score below the base. Docs claim [−100, +150]. Active defaults' −30 pts is offset by bureau-score pts and floored at 0 | `crb_extractor.py:74` |
| H3 | Customer PII (name + full transaction summary) sent to OpenAI by default — cross-border transfer of personal data without DPA 2019 safeguards; no data-processing agreement path | `hybrid_scorer.py:93`, `llm/client.py` |
| H4 | Training pipeline lacks credit-model rigor: single random 80/20 split (no out-of-time validation), no probability calibration (Platt/isotonic), fixed 0.5 threshold, no fairness/disparate-impact metrics, no reject inference | `mlops/trainer.py` |
| H5 | Security: API keys hard-coded in source (`{"dev-key", "prod-key-placeholder"}`); default `admin/admin`; one shared HS256 secret across all services; LMS→scoring call sends no auth at all | `api/credit_reports.py:22`, `external.go:39` |
| H6 | Bureau score normalization assumes one 300–900 scale for all bureaus; Metropol (M-Score) and TransUnion use different ranges/semantics | `crb_extractor.py:36` |

### Medium

| # | Finding | Evidence |
|---|---------|----------|
| M1 | Feedback loop's "auto-retrain" is a stub — drift only writes a row to `data_quality_log`; conversely, if it were wired, auto-promotion without human validation would violate SR 11-7 governance | `feedback/loop.py:101` |
| M2 | PSI monitored only on the PD distribution, not on input features; KS baseline defaults to 0.30 if absent | `feedback/loop.py` |
| M3 | Thin-file customers are punished, not handled: 1 month of history → `income_cv = 1.0` → near-minimum stability score; no "insufficient data" state — engine always emits a confident 300–850 number | `base_scorer.py:71` |
| M4 | Savings-rate feature treats business flow-through as dissaving (SME pays suppliers → looks like negative savings) — bad for the stated SME target market | `base_scorer.py:104` |
| M5 | Score bands differ between engine (Excellent…Poor), LMS mock (A–D), and whitepaper — no single contract; no shared OpenAPI/JSON schema between LMS and scoring engine | `pdo_transformer.py`, `external.go` |
| M6 | All 1,000 customers and 1,533 score events are synthetic seeds; no ingestion pipeline for real transaction data (M-Pesa statements, bank statements, open banking) | `database/`, seeds |
| M7 | Betting penalty and category weights are policy choices with no documented rationale — an examiner will ask; also a proxy-discrimination review has never been done | `llm/prompts.py`, `base_scorer.py` |

---

## 3. Gap Analysis vs International Standards

### 3.1 Model Risk Management — SR 11-7 / Basel / IFRS 9

| Requirement | Status |
|---|---|
| Conceptual soundness documented (development data, feature rationale, binning) | ❌ none — weights are guesses |
| Independent validation before deployment | ❌ no validation function or reports |
| Out-of-time / out-of-sample backtesting | ❌ random split only |
| PD calibration + benchmarking vs external reference (bureau scores) | ❌ fabricated PD |
| Ongoing monitoring (feature-level PSI, KS, override rates) | ⚠️ partial (PD-level PSI/KS gauges exist) |
| Model inventory, versioning, change governance | ⚠️ MLflow registry exists but is decorative (C1) |
| Override / manual-adjustment tracking | ❌ LLM override auto-applied, not tracked as an override |

### 3.2 Explainability & Fairness — EU AI Act (Annex III 5(b)), ECOA-style adverse action

Credit scoring of natural persons is **high-risk** under the EU AI Act — worth treating as the
bar even though Kenya is the market, since it is where international standards are converging:
risk-management system, data governance, technical documentation, human oversight, and "clear
and meaningful explanations" to affected persons.

Gaps: no standardized **reason codes** (top-4 adverse-action reasons); LLM free-text reasoning is
not a substitute (non-deterministic, unvalidated); no human-oversight gate on automated decisions;
no fairness testing (gender/age/region disparate impact); no technical documentation pack.

### 3.3 Kenya Regulatory

| Regulation | Requirement | Status |
|---|---|---|
| CBK Digital Credit Providers Regs 2022 | DCP licence; documented credit policy & **pricing model**; conduct rules | ❌ no pricing model output; licensing artifact pack absent |
| CRB Regulations 2020 | **30-day notice** before negative listing; KSh 1,000 minimum for negative listing; customer's first report free | ❌ no notice workflow in disputes/notifications |
| Data Protection Act 2019 + ODPC Guidance Note for Digital Lenders | Consent before processing, purpose limitation, DPIA, deletion rights, cross-border transfer safeguards | ⚠️ consent table exists; ❌ no deletion flow (already flagged in CLAUDE.md), ❌ DPIA, ❌ OpenAI transfer (H3) |

### 3.4 Security & Ops

- Secrets: move API keys out of source; per-consumer keys; rotate JWT secret; asymmetric (RS256)
  tokens or mTLS between LMS and NemoScore.
- LMS→scoring calls must be authenticated (currently none) and pass through Kong key-auth.
- Enforce TOTP for admin (already scaffolded, not enforced); audit-log immutability (append-only /
  hash-chained) for third-party access log.
- Go services still have **zero unit tests** (Java suite never ported).

---

## 4. Market Benchmark — What Winning Products Have That NemoScore Lacks

### 4.1 African mobile-lending scorers (Tala, Branch, M-Shwari, FairMoney)
- **Real behavioral data**: M-Pesa/mobile-money statement ingestion, airtime purchase patterns,
  device/app metadata (100s–10,000s of micro-features), seasonal income modeling (M-Shwari adapts
  to harvest cycles). NemoScore has 5 hand-crafted features on synthetic transactions.
- **Instant decisioning** measured in seconds with graduated limits: start small, grow limit on
  repayment. No limit-laddering logic exists anywhere in NemoScore/LMS.
- **Default rates ~5%** achieved through iterating models on actual repayment outcomes — the
  feedback loop NemoScore stubs out.

### 4.2 Cash-flow underwriting (Experian Cashflow Score / Credit + Cashflow Score, 2025)
The industry direction: consumer-permissioned bank/wallet data fused with bureau data —
Experian reports ~25–40% predictive lift over bureau-only models. NemoScore's
transactions+CRB hybrid design is *conceptually aligned* — this is its genuine differentiator
once the data and model are real.

### 4.3 Consumer credit products (Credit Karma, CreditWise, myFICO)
Portal pages exist for most of these, but the engines behind them are stubs or absent:
- **Score simulator** backed by the actual model (myFICO-style "what if I repay X"), not canned numbers.
- **Score-change alerts** wired to real score events (notification-service exists; the trigger doesn't).
- **Dispute→bureau workflow** with status tracking and the CRB 30-day notice logic.
- **Score factors / reason codes** shown to the customer ("what's hurting my score").
- **Credit education** localized (KES, CRB listing rules, M-Pesa hygiene tips).

### 4.4 Lender-side scoring platforms (FICO, Zest AI, Indicina, Periculum, Pngme)
- **Reason codes + adverse action API** as a first-class output.
- **Affordability / DTI module** (CBK pricing expectations + responsible lending).
- **Risk-based pricing output**: score → rate/limit recommendation consumed by the LMS
  loan-origination and decision services.
- **Decision strategies**: cutoffs, policy rules, and A/B strategy testing layered on the score —
  the LMS `decision-service` is the natural home; nothing connects them today.
- **Model documentation packs** (model cards, validation reports) generated per version.

---

## 5. What's Genuinely Good (keep and build on)

- Clean service decomposition; shared Go `pkg/athena`; single scoring contract point.
- Hybrid design (cash-flow + bureau + qualitative) matches where the market is going (§4.2).
- MLflow + Prometheus + Grafana + PSI/KS gauges — right observability skeleton.
- Maker-checker on customer creation, consent table, dispute pipeline via RabbitMQ.
- Dual LLM mode (OpenAI/local Ollama) — the local path is the DPA-compliant one; make it default.
- PDO transformer itself is correct math — it just needs a real PD input.

---

## 6. NemoScore Rebuild Roadmap

### Phase 0 — Rebrand & contract hygiene (1–2 weeks)
- Rename branding surfaces (portal, docs, MLflow experiment names, env prefixes) Athena → **NemoScore**;
  keep Go module paths until Phase 3 to avoid churn.
- Define **one versioned score contract** (OpenAPI + JSON schema): score range 300–850, band enum,
  PD, reason codes, `data_sufficiency` flag, model version. LMS and portal consume the same schema.
- Kill the silent mock in the LMS client: fail-closed (route to manual review queue) or return an
  explicit `PROVISIONAL` status that the origination flow must surface. Never `err == nil` with fake data.
- Authenticate LMS→NemoScore calls (service API key via Kong now; mTLS later).

### Phase 1 — Make the score honest (3–4 weeks)
- Wire `lgbm_scorer.predict_pd()` into `compute_hybrid_score` as the PD source; scorecard becomes
  fallback for model-unavailable + a benchmark, and champion/challenger routing becomes real.
- Add **probability calibration** (isotonic on validation set) + out-of-time split in `trainer.py`;
  log calibration curves, Gini/KS/PSI per feature to MLflow.
- Fix CRB extractor: allow negative contribution (documented range), per-bureau score normalization
  (Metropol vs TransUnion), enquiry-velocity feature actually used.
- Demote the LLM: cap at ±25 pts, apply **only within-band** (cannot cross a band boundary), log as a
  tracked override with prompt version; skip entirely for auto-decisions above a risk threshold.
- Add `data_sufficiency` handling: < 3 months of transactions → thin-file path (bureau-only or
  "insufficient data" response), never a confident fabricated score.
- Port the 32 Java unit tests to Go; add contract tests LMS↔NemoScore.

### Phase 2 — Real data (4–6 weeks)
- **M-Pesa statement ingestion** (PDF/CSV parser + categorizer) — the single highest-value feature
  for the Kenyan market; consumer-permissioned upload via the portal, mirroring cash-flow
  underwriting products (§4.2).
- Bank-statement ingestion for SMEs; feature store expansion (velocity, seasonality, merchant
  diversity, income regularity beyond monthly CV — the current 5 features → 30–50).
- Repayment-outcome capture from the LMS (loan status events over RabbitMQ) into training labels —
  this closes the loop the feedback scheduler pretends to have.
- Fix SME features (savings-rate flow-through, M4); seasonal income modeling.

### Phase 3 — Model governance (parallel with Phase 2, 2–3 weeks)
- Validation module: auto-generated model card + validation report (OOT metrics, calibration,
  stability, fairness) per registered version; **human approval gate** before champion promotion.
- Feature-level PSI monitoring; override-rate and reason-code distribution monitoring.
- Fairness testing (gender/age/region proxies) + documented policy-feature rationale (betting, etc.).
- Wire retraining for real, but as "train + register challenger + notify" — never auto-promote.

### Phase 4 — Differentiating features for Nemo neobank (4–6 weeks)
- **Reason codes / adverse action API** (top-4 factors, deterministic, from SHAP + scorecard).
- **Affordability & DTI module** and **risk-based pricing API** (score+PD → limit, rate band) for
  the LMS origination/decision services; graduated limit-laddering for first-time borrowers.
- Real **score simulator** engine (perturb features through the actual model).
- Score-change **alerts** wired end-to-end; dispute workflow with CRB 30-day notice compliance.
- Collections-priority score for the LMS collections-service; fraud-signal exchange with
  fraud-detection-service.

### Phase 5 — Compliance & security pack (2–3 weeks, parallelizable)
- DPA 2019: data-deletion flow, DPIA document, consent granularity per data source,
  **default `LLM_PROVIDER=local`** (Ollama) so PII never leaves the environment.
- CBK DCP licensing artifact pack: credit policy, pricing-model documentation, complaint handling.
- Secrets management (env→vault), per-consumer API keys, RS256 or mTLS, enforce admin TOTP,
  append-only audit log.

### Sequencing note
Phases 0–1 are the credibility gate: until then no demo claim of "AI/ML scoring" is truthful.
Phase 2 is where accuracy actually comes from. Phases 4–5 are where NemoScore becomes a product
rather than an engine.

---

## 7. Architecture Review

**Verdict:** the general shape is right — edge gateway, small services, async events, MLflow +
Prometheus/Grafana observability — but what exists today is **two half-merged platforms** with a
broken integration seam, duplicated infrastructure, and prototype-grade deployment topology.
Findings verified against `docker-compose.yml`, `kong/kong.yml`, `go.work`, and the LMS
`docker-compose.go.yml` overlay.

### 7.1 Critical: the LMS↔scoring seam has never worked as deployed

- LMS `ai-scoring-service` reads `SCORING_API_URL` with default `http://localhost:8200`
  (`cmd/ai-scoring-service/main.go:98`). **No compose/deploy file ever sets it**, and nothing in
  either stack listens on 8200 (python engine = 8001, scoring-service = 8080). Inside a container,
  `localhost:8200` is the container itself → connection refused → silent mock fallback (§2 C3).
- Net effect: in the deployed configuration, **100% of LMS loan-decision scores are fabricated**
  mock values. The two platforms have never exchanged a real score outside manual curl tests.
- Even when pointed correctly, the call bypasses Kong's key-auth (goes to the service directly,
  unauthenticated) and couples to the Python service's internal port instead of the gateway contract.

### 7.2 Structural findings

| # | Finding | Detail |
|---|---------|--------|
| A1 | **Duplicated services across the two stacks** | media-service (8083, `athena_db`) vs go-media-service (8098, `athena_media`); notification-service (8085) vs bff-notification (8111, `athena_bff_notifications`); two user/auth domains. Same capability, different code, different DBs |
| A2 | **No single customer source of truth** | `customers` in `athena_db` vs LMS account-service in `athena_accounts`, keyed differently, reconciled by nothing. For a neobank the customer master is the core entity — this must be settled before feature work |
| A3 | **Three+ gateways** | Kong (:80) for the scoring stack; `lms-api-gateway`; `bff-gateway` + 3 more BFFs with direct-service bypass URLs. Two edge auth schemes (Kong key-auth vs `X-Service-Key`). No unified public edge for Nemo |
| A4 | **Inconsistent DB topology + name collision** | Scoring stack: 6 services share one `athena_db` (shared-database antipattern; GORM AutoMigrate + Flyway leftovers + raw SQL seeds as three competing migration mechanisms). LMS: database-per-service (better). All ~20 databases + MLflow sit in **one unreplicated Postgres container** with default password. Collision: LMS ai-scoring uses DB `athena_scoring` while the actual scoring engine writes to `athena_db` |
| A5 | **Dead legacy component** | Eureka discovery-server (Java, 8761) still runs; Go services don't register, and the LMS Java services it was "kept for" are archived (`_archived_java/`). Pure memory/attack-surface cost |
| A6 | **Cross-repo symlink coupling** | `AthenaCreditScore/go-services -> ../AthenaIntelligentLMS/go-services` + `go.work`; LMS compose overlays Athena compose via `~` paths. Deployability depends on both repos being checked out side-by-side with specific names; already bit once (hardcoded-path fix, commit 0249842) |
| A7 | **Synchronous scoring chain with the LLM in the hot path** | origination → ai-scoring → scoring engine → OpenAI, all blocking (15s timeout). One slow LLM call stalls loan decisions; no retry/backoff, no circuit breaker (the mock fallback is the anti-pattern stand-in), no idempotency keys on report ingestion |
| A8 | **No multi-tenancy in the scoring engine** | LMS issues `tenantId` claims and scopes per tenant; scoring schema (`customers`, `credit_score_events`) has no tenant column. Retrofitting later means a data migration across every scoring table |
| A9 | **Every service publishes host ports** | 8081–8085, 28086–28111, 30100+ — the gateway can be bypassed from the host for any service. Fine for dev; must not survive into prod topology |
| A10 | **No distributed tracing** | Metrics exist (two Prometheus scrape sets, Grafana), but no OpenTelemetry/trace propagation across gateway→Go→Python→LLM — cross-repo debugging is log-grepping. Single-host docker-compose only; no CI running tests; Go services have zero tests to run |

### 7.3 Target architecture for NemoScore (recommendation)

1. **Define NemoScore as the scoring domain only**: scoring-service (Go), python engine, model
   infra (MLflow), CRB adapters, and its own database (`nemoscore_db`) — exposed as **one versioned
   API behind Kong + score events on RabbitMQ**. The neobank platform (LMS repo) owns customer
   master, media, notifications; retire the duplicated Athena copies (A1/A2) gradually.
2. **Fix the seam now (Phase 0)**: set `SCORING_API_URL` to the Kong route with a real consumer
   key; delete the mock fallback; add a contract test in LMS CI that fails if the score API shape drifts.
3. **One public edge** (Kong) in front of lms-api-gateway/BFFs and NemoScore; internal services
   stop publishing host ports (A9); one auth scheme at the edge.
4. **Async scoring path**: `score.requested`/`score.completed` events so origination never blocks
   on the LLM; LLM adjustment moves out of the synchronous path entirely (pairs with the ±cap in §6 Phase 1).
5. **DB hygiene**: scoring gets its own database + versioned SQL migrations (goose/atlas) instead of
   AutoMigrate-in-prod; add `tenant_id` to scoring tables while they're still synthetic (A8 — cheap
   now, expensive later); Postgres backup/PITR strategy before any real data lands.
6. **Decommission Eureka** (A5); service addressing via compose/k8s DNS.
7. **Deployment**: collapse to a single canonical deploy definition (one compose for dev, k3s/k8s
   manifests for anything real) in one deploy repo; add OpenTelemetry tracing across the chain (A10).

These slot into the §6 roadmap: items 2, 3, 6 belong in Phase 0; 4, 5 in Phases 1–2; 1, 7 run
alongside Phases 2–3 as the platform consolidation track.

---

## 8. Sources

- [CBK Digital Credit Providers Regulations 2022](https://www.centralbank.go.ke/2022/03/21/central-bank-of-kenya-digital-credit-providers-regulations-2022/) · [Kenya Law text](https://new.kenyalaw.org/akn/ke/act/ln/2022/46/eng@2022-04-22)
- [CRB Regulations 2020 — CBK press release](https://www.centralbank.go.ke/uploads/press_releases/850440997_Press%20Release%20-%20Credit%20Reference%20Bureau%20Regulations%20-%20April%202020.pdf) · [Oraro & Co overview](https://www.oraro.co.ke/analyse-this-an-overview-of-the-recently-published-credit-reference-bureau-regulations/)
- [ODPC Guidance Note for Digital Credit Providers](https://www.odpc.go.ke/wp-content/uploads/2024/02/ODPC-Guidance-Note-for-Digital-Credit-Providers.pdf)
- [SR 11-7 model risk management requirements](https://www.fluxforce.ai/regulations/us-occ-sr-11-7-model-risk-management) · [IFRS 9 model validation best practices](https://preditta.com/insights/ifrs9-validation) · [Credit risk model validation](https://www.creditbenchmark.com/knowledge-base/credit-risk-model-validation/)
- [EU AI Act & creditworthiness (high-risk, Annex III 5(b))](https://www.regulatoryai.eu/ai-creditworthiness/) · [EBA: AI Act implications for banking](https://www.eba.europa.eu/sites/default/files/2025-11/d8b999ce-a1d9-4964-9606-971bbc2aaf89/AI%20Act%20implications%20for%20the%20EU%20banking%20sector.pdf)
- [Alternative credit scoring in Africa (Tala/Branch/M-Shwari)](https://optimusai.ai/ai-credit-scoring-mobile-money-unbanked/) · [Devex on alternative scoring](https://www.devex.com/news/how-alternative-credit-scoring-is-transforming-lending-in-the-developing-world-88487)
- [Experian Credit + Cashflow Score](https://www.experianplc.com/newsroom/press-releases/2025/experian-announces-first-combined-credit--cash-flow-and-alternat) · [Experian Cashflow Score launch](https://www.experianplc.com/newsroom/press-releases/2025/launch-of-experian-s-cashflow-score-signals-new-era-of-open-bank)
