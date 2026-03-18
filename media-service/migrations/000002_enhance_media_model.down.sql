DROP INDEX IF EXISTS idx_media_files_created_at;
DROP INDEX IF EXISTS idx_media_files_tags;
DROP INDEX IF EXISTS idx_media_files_category;
DROP INDEX IF EXISTS idx_media_files_reference_id;

ALTER TABLE media_files
    DROP COLUMN IF EXISTS reference_id,
    DROP COLUMN IF EXISTS tags,
    DROP COLUMN IF EXISTS is_public,
    DROP COLUMN IF EXISTS thumbnail,
    DROP COLUMN IF EXISTS service_name,
    DROP COLUMN IF EXISTS channel;
