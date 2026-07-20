-- NemoScore multi-tenancy: tenant scoping on all scoring-domain tables.
-- The LMS issues tenantId JWT claims; the scoring engine must be able to
-- partition by tenant before any real data lands (retrofitting later means
-- migrating every table). Default 'nemo' keeps existing rows/flows valid.
--
-- Applied automatically on fresh installs (mounted into initdb after schema),
-- run manually on existing databases:
--   psql -U athena -d athena_db -f database/migrations/2026_07_nemoscore_tenant.sql

ALTER TABLE customers           ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE transactions        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE crb_reports         ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE credit_score_events ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE loans               ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE repayments          ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE feature_values      ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE disputes            ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';
ALTER TABLE consents            ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) NOT NULL DEFAULT 'nemo';

CREATE INDEX IF NOT EXISTS idx_customers_tenant           ON customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_credit_score_events_tenant ON credit_score_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_loans_tenant               ON loans(tenant_id);
