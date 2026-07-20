# CBK Digital Credit Providers — Licensing Artifact Pack (NemoScore inputs)
**Framework:** Central Bank of Kenya (Digital Credit Providers) Regulations, 2022
**Scope:** The scoring-engine artifacts a DCP licence application draws on. The
licence holder is the lender (Nemo neobank); NemoScore supplies the
credit-policy, pricing and complaint-handling substance below.
**Status:** Working draft v1.0, July 2026 — for compliance counsel to assemble
into the application bundle.

---

## 1. Credit policy (Reg. 19 — credit policy requirements)

### 1.1 Scoring methodology
- Hybrid score: 5-dimension behavioural scorecard (income stability/level,
  savings, low-balance, diversity) + CRB contribution [−100, +150] + capped LLM
  qualitative overlay (±25, cannot cross a band) → PD → PDO-calibrated 300–850.
- ML path: LightGBM (`NemoScorer`, MLflow registry) with isotonic PD
  calibration, monotone domain constraints, SHAP-derived adverse-action
  reason codes. Champion promotion is a deliberate human action — never
  automated (governance evidence: model cards + validation reports per
  registered version).
- **Thin-file policy:** applicants with <3 months of data and no bureau file
  return `INSUFFICIENT_DATA` and are never auto-decided; the LMS routes them
  to manual review. This is contractual (nemoscore-api.yaml, fail-closed).

### 1.2 Decisioning policy
- **Affordability (Reg. 21):** DTI = (existing obligations + new installment)
  / gross monthly income, estimated from consumer-permissioned statement data
  when undeclared. AFFORDABLE ≤ 0.40, STRETCHED ≤ 0.50, else UNAFFORDABLE.
- **Limits:** graduated ladder — first-time limits per band (KES 2,000–50,000),
  stepping up 0.5× per successfully closed loan, capped at 6 steps.
- **Collections:** priority scoring (PD + exposure + DPD-stage + promise-to-pay
  behaviour + ability-to-pay). Weak ability-to-pay routes to restructure
  offers, not pressure actions — aligned with Reg. 18 debt-collection conduct
  (no harassment; documented next-best-action ladder).

## 2. Pricing model documentation (Reg. 20 — pricing disclosure)
- Rate construction: `flat monthly rate = base_rate(score band) + (PD × LGD)/12`,
  hard-capped at 15%/month. Bands and caps are configuration
  (`PRICING_RATE_BANDS`, `PRICING_LGD=0.55`, `PRICING_MAX_MONTHLY_RATE`), so the
  filed pricing schedule and the running system share one source of truth —
  the API echoes the live tables (`rate_band_table`) for disclosure.
- Total cost of credit: `total repayable = P × (1 + r × term)`; the
  affordability response returns installment and total_repayable for
  pre-contract disclosure (Reg. 20(2) requires disclosure before drawdown).
- No rollover-fee or hidden-charge mechanics exist in the engine.

## 3. Complaint handling (Reg. 33)
- **Channel:** portal dispute workflow (customer files → RabbitMQ event →
  admin queue → resolution states OPEN/RESOLVED/CLOSED, `disputed_field`
  captured per CRB practice).
- **CRB corrections:** disputes affecting bureau data follow the 30-day CRB
  notice path.
- **Audit:** dispute lifecycle events are persisted (`disputes`,
  notification log); admin actions require authenticated roles.
- **SLA to file:** acknowledge within 48h, resolve or escalate within 30 days
  (operational SLA to be ratified by the lender's complaints officer).

## 4. Data protection interface (Reg. 32 → DPA 2019)
See `docs/compliance/dpia.md` — consent-based statement ingestion, erasure
flow, local-by-default LLM, reason codes for adverse action.

## 5. Evidence index (for the application bundle)
| Artifact | Location |
|---|---|
| API contract (decisioning surface) | `docs/nemoscore-api.yaml` (1.5.0) |
| Model governance (cards, validation, promotion gate) | MLflow registry + `mlops/` |
| Reason-code catalogue (NSxx) | `athena-python-service/scoring/reason_codes.py` |
| Pricing configuration | `athena-python-service/scoring/pricing.py` + env |
| DPIA | `docs/compliance/dpia.md` |
| System audit & roadmap | `docs/nemoscore-audit.md` |
| Erasure log schema | `database/migrations/2026_07_privacy_erasure.sql` |

## 6. Known gaps (tracked, not blocking a draft filing)
- Fairness test evidence thin until real repayment labels accumulate
  (label loop is live; first quarterly review pending).
- Retention schedule and complaints SLA need lender ratification.
- Secrets vaulting and key rotation are engineering backlog (Phase 5).
