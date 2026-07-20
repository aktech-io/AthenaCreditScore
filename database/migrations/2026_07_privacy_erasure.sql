-- DPA 2019 right-to-erasure support (NemoScore Phase 5).
-- erasure_log records every executed erasure: who asked, when, what was
-- touched. The log itself holds no personal data beyond the numeric
-- customer_id (which survives as a tombstone in `customers`).
--
-- Apply by hand to already-initialized DBs (initdb won't rerun):
--   docker exec -i athena-postgres psql -U athena -d athena_db < database/migrations/2026_07_privacy_erasure.sql
-- and to the live Contabo nemoscore postgres. Also mirrored in schema.sql.

CREATE TABLE IF NOT EXISTS erasure_log (
    erasure_id      BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    tenant_id       VARCHAR(64) NOT NULL DEFAULT 'nemo',
    requested_by    VARCHAR(100) NOT NULL,   -- JWT sub / 'service'
    tables_touched  JSONB NOT NULL,          -- {"table": rows_affected, ...}
    erased_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
