-- Score-change alerts (NemoScore Phase 4, contract 1.5.0).
-- score_alerts is the per-customer alert feed backing the portal Alerts page
-- (persisted whether or not the email/SMS publish succeeds); alert_preferences
-- is the per-customer opt-out + threshold override.
--
-- Apply by hand to already-initialized DBs (initdb won't rerun):
--   docker exec -i athena-postgres psql -U athena -d athena_db < database/migrations/2026_07_score_alerts.sql
-- and to the live Contabo nemoscore postgres. Also mirrored in schema.sql.

CREATE TABLE IF NOT EXISTS score_alerts (
    alert_id        BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    tenant_id       VARCHAR(64) NOT NULL DEFAULT 'nemo',
    alert_type      VARCHAR(32) NOT NULL DEFAULT 'SCORE_CHANGE',
    reason          VARCHAR(32) NOT NULL,            -- BAND_CHANGE | SCORE_DELTA
    previous_score  INTEGER NOT NULL,
    new_score       INTEGER NOT NULL,
    delta           INTEGER NOT NULL,                -- new - previous (signed)
    previous_band   VARCHAR(32),
    new_band        VARCHAR(32),
    notified        BOOLEAN NOT NULL DEFAULT FALSE,  -- notification event published
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_score_alerts_customer
    ON score_alerts (customer_id, created_at DESC);

CREATE TABLE IF NOT EXISTS alert_preferences (
    customer_id          BIGINT PRIMARY KEY,
    score_change_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    min_delta            INTEGER,                    -- NULL -> service default (SCORE_ALERT_MIN_DELTA)
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
