-- Rollback: remove maker-checker audit columns and identity document reference
DROP INDEX IF EXISTS idx_customers_created_by;
DROP INDEX IF EXISTS idx_customers_verification_status;

ALTER TABLE customers DROP COLUMN IF EXISTS identity_document_id;
ALTER TABLE customers DROP COLUMN IF EXISTS rejection_reason;
ALTER TABLE customers DROP COLUMN IF EXISTS approved_at;
ALTER TABLE customers DROP COLUMN IF EXISTS approved_by;
ALTER TABLE customers DROP COLUMN IF EXISTS created_by;
