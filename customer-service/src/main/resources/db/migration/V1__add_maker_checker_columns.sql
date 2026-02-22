-- V1: Add maker-checker audit columns and identity document reference to customers table
ALTER TABLE customers ADD COLUMN IF NOT EXISTS created_by            VARCHAR(255);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS approved_by           VARCHAR(255);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS approved_at           TIMESTAMP;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS rejection_reason      VARCHAR(500);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS identity_document_id  UUID;

-- Indexes for approval queue and lookup
CREATE INDEX IF NOT EXISTS idx_customers_verification_status ON customers(verification_status);
CREATE INDEX IF NOT EXISTS idx_customers_created_by           ON customers(created_by);
