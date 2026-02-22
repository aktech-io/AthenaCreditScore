-- V2: Enhance media_files table with general-purpose media management fields

ALTER TABLE media_files
    ADD COLUMN IF NOT EXISTS reference_id UUID,
    ADD COLUMN IF NOT EXISTS tags VARCHAR(500),
    ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS thumbnail VARCHAR(255),
    ADD COLUMN IF NOT EXISTS service_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS channel VARCHAR(255);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_media_files_reference_id ON media_files(reference_id);
CREATE INDEX IF NOT EXISTS idx_media_files_category ON media_files(category);
CREATE INDEX IF NOT EXISTS idx_media_files_tags ON media_files(tags);
CREATE INDEX IF NOT EXISTS idx_media_files_created_at ON media_files(created_at);
