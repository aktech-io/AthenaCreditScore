-- Training labels from real LMS repayment outcomes (NemoScore Phase 2).
-- Populated by athena-python-service listeners/loan_outcomes.py, which consumes
-- loan lifecycle events (loan.closed / loan.written.off / loan.stage.changed)
-- from the LMS topic exchange `athena.lms.exchange`.
--
-- customer_id is the SAME int64 id NemoScore scores under. For non-numeric LMS
-- customer ids (CUST-…, EODINT-…) that is the LMS ai-scoring FlexibleCustomerID
-- hash (h = h*31 + rune over the string, abs via float64) — such ids may not
-- exist in `customers`, so there is deliberately NO foreign key here.
--
-- Dedupe: one row per (loan_ref, event_type); redelivered events upsert.
-- The training frame takes MAX(default_flag) per loan_ref, so a later
-- loan.written.off overrides an earlier on-time-looking loan.closed.
--
-- Safe to run repeatedly.

CREATE TABLE IF NOT EXISTS training_labels (
    label_id     BIGSERIAL PRIMARY KEY,
    customer_id  BIGINT NOT NULL,
    loan_ref     VARCHAR(100) NOT NULL,
    event_type   VARCHAR(50) NOT NULL,
    default_flag SMALLINT NOT NULL CHECK (default_flag IN (0, 1)),
    observed_at  TIMESTAMPTZ NOT NULL,
    tenant_id    VARCHAR(50) NOT NULL DEFAULT 'nemo',
    source       VARCHAR(30) NOT NULL DEFAULT 'LMS_EVENT',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (loan_ref, event_type)
);

CREATE INDEX IF NOT EXISTS idx_training_labels_customer
    ON training_labels(customer_id);
