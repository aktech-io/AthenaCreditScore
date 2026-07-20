-- NemoScore Phase 4: deterministic adverse-action reason codes.
-- Stored per scoring event as JSONB: [{"code": "NS03", "description": "..."}, ...]
-- Applied automatically on fresh installs (mounted into initdb after schema),
-- run manually on existing databases:
--   psql -U athena -d athena_db -f database/migrations/2026_07_reason_codes.sql

ALTER TABLE credit_score_events ADD COLUMN IF NOT EXISTS reason_codes JSONB NOT NULL DEFAULT '[]';
