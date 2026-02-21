-- ============================================================================
-- Athena Credit Initiative — PostgreSQL Schema
-- Version: 2.0 (Enhanced with MLOps + Feature Store + Portal extensions)
-- ============================================================================

-- Core dimension data
CREATE TABLE customers (
    customer_id     BIGSERIAL PRIMARY KEY,
    national_id     VARCHAR(20) UNIQUE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    middle_name     VARCHAR(100),
    mobile_number   VARCHAR(20) UNIQUE,
    email           VARCHAR(150),
    date_of_birth   DATE,
    gender          VARCHAR(10),
    region          VARCHAR(100),
    county          VARCHAR(100),    -- standardised via geocoder
    sub_county      VARCHAR(100),
    ward            VARCHAR(100),
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    id_type         VARCHAR(30),
    id_expiry_date  DATE,
    bank_name       VARCHAR(100),
    branch_name     VARCHAR(100),
    account_number  VARCHAR(50),
    mifos_client_id VARCHAR(50),     -- Mifos/Fineract external ID
    registration_channel VARCHAR(30) DEFAULT 'ADMIN_PORTAL',
    verification_status  VARCHAR(20) DEFAULT 'PENDING',
    crb_consent     BOOLEAN DEFAULT FALSE,
    crb_consent_at  TIMESTAMPTZ,
    whitelisted     BOOLEAN DEFAULT FALSE,
    credit_score    NUMERIC(6,2),
    created_by      VARCHAR(100),
    approved_by     VARCHAR(100),
    approved_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transactions (
    transaction_id      BIGSERIAL PRIMARY KEY,
    customer_id         BIGINT NOT NULL REFERENCES customers(customer_id),
    transaction_date    DATE NOT NULL,
    amount              NUMERIC(18,2) NOT NULL,
    transaction_type    VARCHAR(30) NOT NULL,  -- CREDIT | DEBIT
    category            VARCHAR(50),           -- SALARY | UTILITY | GROCERIES | BETTING ...
    description         TEXT,
    channel             VARCHAR(30),           -- MIFOS | MPESA | BANK
    balance_after       NUMERIC(18,2),
    external_ref        VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_date     ON transactions(transaction_date);

CREATE TABLE crb_reports (
    report_id           BIGSERIAL PRIMARY KEY,
    customer_id         BIGINT NOT NULL REFERENCES customers(customer_id),
    crb_name            VARCHAR(50) NOT NULL,  -- TransUnion | Metropol
    report_date         DATE NOT NULL,
    bureau_score        INTEGER,
    raw_report          JSONB NOT NULL,
    extracted_metrics   JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crb_reports_customer ON crb_reports(customer_id);

CREATE TABLE base_score_breakdowns (
    breakdown_id            BIGSERIAL PRIMARY KEY,
    score_event_id          BIGINT,    -- foreign key added after credit_score_events
    income_stability_score  NUMERIC(5,2),
    avg_monthly_income      NUMERIC(18,2),
    savings_rate_score      NUMERIC(5,2),
    low_balance_score       NUMERIC(5,2),
    transaction_diversity   NUMERIC(5,2),
    base_total              NUMERIC(6,2),
    analysis_period_days    INTEGER,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE credit_score_events (
    event_id            BIGSERIAL PRIMARY KEY,
    customer_id         BIGINT NOT NULL REFERENCES customers(customer_id),
    base_score          NUMERIC(6,2),
    crb_contribution    NUMERIC(6,2),
    llm_adjustment      NUMERIC(6,2),
    pd_probability      NUMERIC(8,6),  -- raw probability of default
    final_score         NUMERIC(6,2),  -- PDO-scaled score 300-850
    score_band          VARCHAR(30),
    reasoning           TEXT,
    crb_report_id       BIGINT REFERENCES crb_reports(report_id),
    breakdown_id        BIGINT REFERENCES base_score_breakdowns(breakdown_id),
    model_version_id    BIGINT,        -- foreign key added after model_versions
    model_target        VARCHAR(20) DEFAULT 'champion',
    llm_provider        VARCHAR(20),   -- openai | local
    llm_model_name      VARCHAR(50),
    scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_score_events_customer ON credit_score_events(customer_id);
CREATE INDEX idx_score_events_scored   ON credit_score_events(scored_at);

ALTER TABLE base_score_breakdowns
    ADD CONSTRAINT fk_breakdown_event
    FOREIGN KEY (score_event_id) REFERENCES credit_score_events(event_id);

CREATE TABLE loans (
    loan_id             BIGSERIAL PRIMARY KEY,
    customer_id         BIGINT NOT NULL REFERENCES customers(customer_id),
    score_event_id      BIGINT REFERENCES credit_score_events(event_id),
    principal_amount    NUMERIC(18,2) NOT NULL,
    interest_rate       NUMERIC(5,4) NOT NULL,
    tenure_months       INTEGER NOT NULL,
    disbursement_date   DATE,
    maturity_date       DATE,
    status              VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE | CLOSED | DEFAULT
    external_loan_id    VARCHAR(100),   -- Mifos loan ID
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_loans_customer ON loans(customer_id);

CREATE TABLE repayments (
    repayment_id        BIGSERIAL PRIMARY KEY,
    loan_id             BIGINT NOT NULL REFERENCES loans(loan_id),
    customer_id         BIGINT NOT NULL REFERENCES customers(customer_id),
    payment_date        DATE NOT NULL,
    amount_paid         NUMERIC(18,2) NOT NULL,
    days_late           INTEGER DEFAULT 0,
    penalty_amount      NUMERIC(18,2) DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_repayments_loan     ON repayments(loan_id);
CREATE INDEX idx_repayments_customer ON repayments(customer_id);

-- ─── MLOps & Feature Store ─────────────────────────────────────────────────

CREATE TABLE model_versions (
    version_id      BIGSERIAL PRIMARY KEY,
    mlflow_run_id   VARCHAR(100) UNIQUE,
    model_name      VARCHAR(100) DEFAULT 'AthenaScorer',
    alias           VARCHAR(20)  DEFAULT 'challenger', -- champion | challenger
    auc_roc         NUMERIC(6,4),
    ks_statistic    NUMERIC(6,4),
    pr_auc          NUMERIC(6,4),
    f1_score        NUMERIC(6,4),
    feature_list    JSONB,
    insights_json   JSONB,         -- SHAP top factors from last run
    is_active       BOOLEAN DEFAULT TRUE,
    trained_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE credit_score_events
    ADD CONSTRAINT fk_score_event_model
    FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id);

CREATE TABLE feature_definitions (
    feature_id      BIGSERIAL PRIMARY KEY,
    feature_name    VARCHAR(100) UNIQUE NOT NULL,
    feature_group   VARCHAR(50),  -- application | performance | crb | encoded_cat
    sql_template    TEXT,
    python_fn       TEXT,
    data_type       VARCHAR(30),
    version         INTEGER DEFAULT 1,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE feature_values (
    fv_id           BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    feature_id      BIGINT NOT NULL REFERENCES feature_definitions(feature_id),
    feature_version INTEGER NOT NULL,
    value_numeric   NUMERIC(20,6),
    value_text      TEXT,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (customer_id, feature_id, feature_version)
);
CREATE INDEX idx_feature_values_customer ON feature_values(customer_id);

CREATE TABLE routing_config (
    config_id           BIGSERIAL PRIMARY KEY,
    champion_version_id BIGINT REFERENCES model_versions(version_id),
    challenger_version_id BIGINT REFERENCES model_versions(version_id),
    challenger_pct      NUMERIC(4,3) DEFAULT 0.0,  -- 0.0 to 1.0
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE champion_challenger_log (
    log_id          BIGSERIAL PRIMARY KEY,
    score_event_id  BIGINT REFERENCES credit_score_events(event_id),
    model_target    VARCHAR(20),  -- champion | challenger
    version_id      BIGINT REFERENCES model_versions(version_id),
    logged_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE psi_monitoring (
    psi_id          BIGSERIAL PRIMARY KEY,
    feature_name    VARCHAR(100) NOT NULL,
    psi_value       NUMERIC(8,4),
    sample_date     DATE NOT NULL,
    bucket_json     JSONB,
    alert_triggered BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE data_quality_log (
    dq_id           BIGSERIAL PRIMARY KEY,
    batch_date      DATE NOT NULL,
    table_name      VARCHAR(100),
    field_name      VARCHAR(100),
    missing_count   INTEGER DEFAULT 0,
    invalid_count   INTEGER DEFAULT 0,
    total_count     INTEGER,
    missing_rate    NUMERIC(6,4),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Auth & Portal ─────────────────────────────────────────────────────────

-- Extends user-service User model for customer authentication
CREATE TABLE auth_users (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT REFERENCES customers(customer_id),
    username        VARCHAR(100) UNIQUE NOT NULL,  -- mobile number for customers
    password_hash   VARCHAR(255),
    phone           VARCHAR(20) UNIQUE,
    otp_code        VARCHAR(6),
    otp_expires_at  TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE admin_users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    email           VARCHAR(150),
    role            VARCHAR(30) NOT NULL CHECK (role IN ('ADMIN','ANALYST','VIEWER','CREDIT_RISK')),
    totp_secret     VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Notification config (reused from notification-service pattern)
CREATE TABLE notification_config (
    id              BIGSERIAL PRIMARY KEY,
    type            VARCHAR(20) UNIQUE NOT NULL,    -- EMAIL | SMS
    provider        VARCHAR(50),
    host            VARCHAR(200),
    port            INTEGER,
    username        VARCHAR(100),
    password        VARCHAR(255),
    from_address    VARCHAR(150),
    api_key         VARCHAR(255),
    api_secret      VARCHAR(255),
    sender_id       VARCHAR(50),
    enabled         BOOLEAN DEFAULT FALSE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notification_log (
    id              BIGSERIAL PRIMARY KEY,
    service_name    VARCHAR(100),
    type            VARCHAR(20),
    recipient       VARCHAR(200),
    subject         VARCHAR(300),
    body            TEXT,
    status          VARCHAR(20),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE disputes (
    dispute_id      BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    report_id       BIGINT REFERENCES crb_reports(report_id),
    reason          TEXT NOT NULL,
    status          VARCHAR(30) DEFAULT 'OPEN' CHECK (status IN ('OPEN','UNDER_REVIEW','RESOLVED','REJECTED')),
    resolution      TEXT,
    resolved_by     VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE consents (
    consent_id      BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
    partner_id      BIGINT NOT NULL,
    scope           VARCHAR(100),
    token_jti       VARCHAR(100) UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE api_keys (
    key_id          BIGSERIAL PRIMARY KEY,
    partner_name    VARCHAR(100) NOT NULL,
    api_key_hash    VARCHAR(255) UNIQUE NOT NULL,
    allowed_ips     TEXT[],
    rate_limit      INTEGER DEFAULT 1000,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
    log_id          BIGSERIAL PRIMARY KEY,
    actor_type      VARCHAR(20),   -- CUSTOMER | ADMIN | PARTNER | SYSTEM
    actor_id        VARCHAR(100),
    action          VARCHAR(100),
    resource        VARCHAR(100),
    ip_address      INET,
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_id, created_at);

-- ─── Seed data: default routing config ────────────────────────────────────
INSERT INTO routing_config (challenger_pct) VALUES (0.0);
INSERT INTO notification_config (type, enabled) VALUES ('EMAIL', FALSE);
INSERT INTO notification_config (type, enabled) VALUES ('SMS', FALSE);
