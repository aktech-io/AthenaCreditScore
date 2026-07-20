-- Score-event honesty (NemoScore): persist scoring status + provenance.
--
-- The POST /api/v1/credit-reports response already reports status,
-- data_sufficiency, pd_source and model_version, but none were persisted —
-- so GET /api/v1/credit-score/{id} fabricated status='SCORED' even for
-- INSUFFICIENT_DATA runs, breaking the fail-closed contract for the LMS.
--
-- model_version is the MLflow registry version string of the PD model that
-- served the request (distinct from model_version_id, the legacy FK to the
-- local model_versions table).
--
-- Safe to run repeatedly.

ALTER TABLE credit_score_events
    ADD COLUMN IF NOT EXISTS status           VARCHAR(20) NOT NULL DEFAULT 'SCORED',
    ADD COLUMN IF NOT EXISTS data_sufficiency VARCHAR(12) NOT NULL DEFAULT 'FULL',
    ADD COLUMN IF NOT EXISTS pd_source        VARCHAR(40),
    ADD COLUMN IF NOT EXISTS model_version    VARCHAR(40);
