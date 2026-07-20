# Data Protection Impact Assessment — NemoScore
**System:** NemoScore credit scoring engine (Nemo neobank platform)
**Framework:** Kenya Data Protection Act, 2019 (DPA) + Data Protection (General) Regulations, 2021
**Status:** Working draft for DPO review — v1.0, July 2026
**Related:** `docs/nemoscore-api.yaml` (data surface), `docs/nemoscore-audit.md` (system audit)

> DPA §31 requires a DPIA where processing is "likely to result in high risk to the
> rights and freedoms of a data subject". Automated credit scoring of individuals is
> squarely in scope.

---

## 1. Processing description

### 1.1 Purpose
Produce a 300–850 credit score and probability of default (PD) for loan
origination, pricing, affordability, collections prioritization, and score-change
alerts, for customers of the Nemo neobank (LMS).

### 1.2 Data categories processed
| Category | Fields | Source | Tables |
|---|---|---|---|
| Identity | name, national ID, DOB, gender | customer onboarding | `customers` |
| Contact | mobile, email | onboarding | `customers` |
| Location | region/county/ward, lat/long | onboarding | `customers` |
| Financial behaviour | transaction amounts/dates/descriptions | LMS, M-Pesa/bank statements | `transactions`, `mpesa_*`, `bank_*` |
| Bureau data | bureau score, NPAs, account history | TransUnion/Metropol CRBs | `crb_reports` |
| Derived | score, PD, feature vectors, reason codes | computed | `credit_score_events`, `lgbm_features` |

### 1.3 Lawful basis
- **Consent** for consumer-permissioned statement uploads (the customer uploads
  their own M-Pesa/bank statement; ADMIN/ANALYST uploads require recorded consent).
- **Legitimate interest / contract performance** for scoring loan applicants
  (creditworthiness assessment is intrinsic to the credit contract).
- **Legal obligation** for CRB data sharing (CBK/CRB regulations mandate
  participation in credit information sharing).
- Partner data sharing is gated on `consents` rows (scope + expiry + revocation),
  enforced at the third-party gateway.

### 1.4 Automated decision-making (DPA §35)
Scores are decision inputs to the LMS. Mitigations for §35 rights:
- **Thin files are never auto-decided** — `INSUFFICIENT_DATA` forces manual review
  (fail-closed contract; the LMS marks these SKIPPED).
- **Adverse-action reason codes** (top-4, deterministic NSxx) accompany every score
  so a declined applicant can be told why.
- **Dispute workflow** exists in the customer portal; disputes route to human review.
- The LLM adjustment is capped (±25) and can never move a score across a band
  boundary — no opaque model can flip a decision on its own.

---

## 2. Necessity & proportionality
- Feature set is aggregate behavioural data (monthly CVs, ratios, streaks) —
  raw transaction text is not a model input.
- **Betting ratio** is a scored feature; its policy rationale (documented
  affordability risk, not moral judgment) is recorded in the model card per
  registered version.
- Monotone constraints prevent the model learning indefensible directions
  (e.g. higher bureau score raising PD), which is both a validity and a
  fairness control.
- Data minimization gap (accepted, tracked): `customers` carries onboarding
  fields (ward, lat/long) the scorer does not use; they support KYC, not scoring.

---

## 3. Risks & mitigations

| # | Risk | Likelihood | Impact | Mitigations |
|---|---|---|---|---|
| R1 | PII leaves the environment via hosted LLM | Med | High | **Default `LLM_PROVIDER=local`** (Ollama in-cluster); hosted OpenAI is an explicit opt-in; prompts exclude identifiers beyond name |
| R2 | Statement upload abuse (uploading someone else's statement) | Med | Med | Customers can upload only their own (JWT customerId check); staff uploads are role-gated and logged |
| R3 | Unauthorized score access | Med | High | JWT/X-Api-Key on every endpoint; customer tokens scoped to own id; service keys via `SERVICE_API_KEYS`; Kong rate limiting |
| R4 | Discriminatory outcomes | Med | High | No protected attributes as features; fairness testing on gender/age/region proxies is in the governance loop (feature PSI + model card); human promotion gate |
| R5 | Data breach of raw statements | Low | High | Raw rows live only in postgres (no object storage copies); TLS at the edge; erasure flow deletes raw statements outright |
| R6 | Indefinite retention | Med | Med | Erasure flow (below); decision records retained under documented lawful basis; retention schedule owned by DPO |
| R7 | Alert SMS/email to a stale contact | Low | Med | Alerts read contact at send time from `customers`; erasure nulls contacts, which silences alerts |

---

## 4. Data subject rights — implementation status

| Right | Status | Mechanism |
|---|---|---|
| Access | ✅ | Client portal: score, full report, reason codes, alert history |
| Rectification | ✅ | Dispute workflow (portal → admin review → CRB 30-day notice path) |
| **Erasure** | ✅ | `POST /api/v1/credit-score/{id}/erasure` (ADMIN/SERVICE, confirmation string, logged in `erasure_log`). Erases/pseudonymizes PII, deletes raw statements + feature vectors; retains numeric decision records (score/PD/reason codes) under lawful-retention basis. Media files and user accounts are erased via their services' own admin APIs — the DPO runbook chains all three. |
| Objection to automated decision | ✅ | Manual-review path (INSUFFICIENT_DATA + dispute escalation) |
| Portability | ⚠️ Partial | Score history retrievable via API; machine-readable export bundle is a follow-up |

---

## 5. Residual risk & sign-off
Residual risks R4 (fairness evidence still maturing until real repayment labels
accumulate) and R6 (retention schedule not yet ratified) are accepted for pilot
scale and reviewed at each model promotion. Secrets management (env → vault) and
key rotation are tracked in the Phase 5 backlog (`CLAUDE.md` → Outstanding).

| Role | Name | Date |
|---|---|---|
| Data Protection Officer | _pending_ | |
| Head of Credit Risk | _pending_ | |
| Engineering | _pending_ | |
