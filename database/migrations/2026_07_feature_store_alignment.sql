-- Align the live feature-store tables with database/schema.sql (the canonical
-- shape used by features/feature_store.py): JSONB vector snapshots keyed by a
-- feature-set definition. The legacy per-feature-row tables (feature_id /
-- value_numeric) were created by an earlier schema revision, were never
-- written to (verified empty), and no code path reads them.
--
-- Safe to run repeatedly; only rebuilds when the legacy shape is detected.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'feature_definitions' AND column_name = 'feature_name'
    ) THEN
        DROP TABLE IF EXISTS feature_values;
        DROP TABLE IF EXISTS feature_definitions;

        CREATE TABLE feature_definitions (
            definition_id    BIGSERIAL PRIMARY KEY,
            feature_set_name VARCHAR(100) NOT NULL,
            version          VARCHAR(20) NOT NULL,
            feature_names    JSONB NOT NULL,
            description      TEXT,
            encoding_config  JSONB,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (feature_set_name, version)
        );

        CREATE TABLE feature_values (
            value_id       BIGSERIAL PRIMARY KEY,
            customer_id    BIGINT NOT NULL REFERENCES customers(customer_id),
            definition_id  BIGINT NOT NULL REFERENCES feature_definitions(definition_id),
            feature_vector JSONB NOT NULL,
            computed_at    DATE NOT NULL DEFAULT CURRENT_DATE,
            tenant_id      VARCHAR(50) NOT NULL DEFAULT 'nemo',
            UNIQUE (customer_id, definition_id, computed_at)
        );
        CREATE INDEX idx_feature_values_customer ON feature_values(customer_id);
    END IF;
END $$;
