CREATE TABLE IF NOT EXISTS media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id BIGINT,
    category VARCHAR(50) NOT NULL,
    media_type VARCHAR(50) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    stored_filename VARCHAR(500) NOT NULL,
    content_type VARCHAR(200) NOT NULL,
    file_size BIGINT,
    uploaded_by VARCHAR(200),
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_files_customer_id ON media_files(customer_id);
CREATE INDEX IF NOT EXISTS idx_media_files_status ON media_files(status);
