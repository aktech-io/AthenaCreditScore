-- M-Pesa statement ingestion (NemoScore Phase 2 — real behavioral data).
-- Consumer-permissioned statement uploads are parsed into per-transaction rows
-- that feed the lgbm_features v2 cash-flow features (features/pipeline.py).
--
-- Dedupe strategy:
--   - a re-uploaded identical file is rejected via (customer_id, file_sha256);
--   - overlapping statement periods are handled per-row via
--     (customer_id, receipt_no) — M-Pesa receipt numbers are globally unique.
--
-- Safe to run repeatedly.

CREATE TABLE IF NOT EXISTS mpesa_statements (
    statement_id    BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    source_format   VARCHAR(10) NOT NULL CHECK (source_format IN ('CSV', 'PDF')),
    file_sha256     VARCHAR(64) NOT NULL,
    period_start    DATE,
    period_end      DATE,
    n_transactions  INTEGER NOT NULL DEFAULT 0,
    n_duplicates    INTEGER NOT NULL DEFAULT 0,
    tenant_id       VARCHAR(50) NOT NULL DEFAULT 'nemo',
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (customer_id, file_sha256)
);

CREATE TABLE IF NOT EXISTS mpesa_transactions (
    txn_id          BIGSERIAL PRIMARY KEY,
    statement_id    BIGINT NOT NULL REFERENCES mpesa_statements(statement_id) ON DELETE CASCADE,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    receipt_no      VARCHAR(20) NOT NULL,
    txn_time        TIMESTAMPTZ NOT NULL,
    details         TEXT NOT NULL,
    category        VARCHAR(30) NOT NULL,
    direction       VARCHAR(3) NOT NULL CHECK (direction IN ('IN', 'OUT')),
    amount          NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
    balance         NUMERIC(14,2),
    counterparty    VARCHAR(200),
    tenant_id       VARCHAR(50) NOT NULL DEFAULT 'nemo',
    UNIQUE (customer_id, receipt_no)
);

CREATE INDEX IF NOT EXISTS idx_mpesa_txn_customer_time
    ON mpesa_transactions(customer_id, txn_time);
