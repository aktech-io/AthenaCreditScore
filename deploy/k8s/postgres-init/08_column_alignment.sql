-- Columns the running code depends on that exist in the live compose database
-- but are missing from database/schema.sql + the shipped migrations (they were
-- applied manually to the compose DB at some point). Found by diffing
-- information_schema.columns between the compose athena_db and a fresh initdb
-- (2026-07-20). Without these, GET /api/v1/credit-score/{id} 500s
-- (api/scoring.py selects credit_score_events.status/pd_source/...).
ALTER TABLE credit_score_events
    ADD COLUMN IF NOT EXISTS status           VARCHAR(20) NOT NULL DEFAULT 'SCORED',
    ADD COLUMN IF NOT EXISTS data_sufficiency VARCHAR(12) NOT NULL DEFAULT 'FULL',
    ADD COLUMN IF NOT EXISTS pd_source        VARCHAR(40),
    ADD COLUMN IF NOT EXISTS model_version    VARCHAR(40);

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS identity_document_id UUID;

ALTER TABLE disputes
    ADD COLUMN IF NOT EXISTS disputed_field VARCHAR(100);
