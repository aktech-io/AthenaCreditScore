-- SME bank-statement ingestion (NemoScore Phase 2 — real behavioral data).
-- Consumer-permissioned bank statement uploads (KCB, Equity, Co-op, Absa,
-- NCBA, ...) are parsed into per-transaction rows that feed the lgbm_features
-- v3 SME cash-flow features (features/pipeline.py).
--
-- Dedupe strategy:
--   - a re-uploaded identical file is rejected via (customer_id, file_sha256);
--   - overlapping statement periods are handled per-row via
--     (customer_id, row_hash) — banks lack universal receipt numbers, so
--     row_hash is a deterministic sha256 of (normalized date | amount |
--     direction | balance | details), computed in ingestion/bank.py.
--
-- Safe to run repeatedly.

CREATE TABLE IF NOT EXISTS bank_statements (
    statement_id    BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    bank_name       VARCHAR(100),
    source_format   VARCHAR(10) NOT NULL CHECK (source_format IN ('CSV', 'PDF')),
    file_sha256     VARCHAR(64) NOT NULL,
    period_start    DATE,
    period_end      DATE,
    n_transactions  INTEGER NOT NULL DEFAULT 0,
    n_duplicates    INTEGER NOT NULL DEFAULT 0,
    tenant_id       VARCHAR(50) NOT NULL DEFAULT 'nemo',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (customer_id, file_sha256)
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    txn_id          BIGSERIAL PRIMARY KEY,
    statement_id    BIGINT NOT NULL REFERENCES bank_statements(statement_id) ON DELETE CASCADE,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    row_hash        VARCHAR(64) NOT NULL,
    txn_time        TIMESTAMPTZ NOT NULL,
    details         TEXT NOT NULL,
    category        VARCHAR(30) NOT NULL,
    direction       VARCHAR(3) NOT NULL CHECK (direction IN ('IN', 'OUT')),
    amount          NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
    balance         NUMERIC(14,2),
    reference       VARCHAR(100),
    tenant_id       VARCHAR(50) NOT NULL DEFAULT 'nemo',
    UNIQUE (customer_id, row_hash)
);

CREATE INDEX IF NOT EXISTS idx_bank_txn_customer_time
    ON bank_transactions(customer_id, txn_time);
