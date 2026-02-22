-- V2: Add disputed_field column to disputes table
-- Allows storing the specific credit field being disputed (npa_count, bureau_score, etc.)
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS disputed_field VARCHAR(100);
