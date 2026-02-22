-- V1: Notification service schema

CREATE TABLE IF NOT EXISTS notification_configs (
    id          BIGSERIAL PRIMARY KEY,
    type        VARCHAR(20) NOT NULL UNIQUE,  -- EMAIL, SMS
    provider    VARCHAR(50),
    host        VARCHAR(255),
    port        INTEGER,
    username    VARCHAR(255),
    password    VARCHAR(255),
    from_address VARCHAR(255),
    api_key     VARCHAR(255),
    api_secret  VARCHAR(255),
    sender_id   VARCHAR(50),
    enabled     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id            BIGSERIAL PRIMARY KEY,
    service_name  VARCHAR(100) NOT NULL,
    type          VARCHAR(20)  NOT NULL,
    recipient     VARCHAR(255) NOT NULL,
    subject       VARCHAR(500),
    body          TEXT,
    status        VARCHAR(20)  NOT NULL,  -- SENT, FAILED, SKIPPED
    error_message TEXT,
    sent_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_logs_recipient    ON notification_logs(recipient);
CREATE INDEX IF NOT EXISTS idx_notification_logs_service_name ON notification_logs(service_name);
CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_at      ON notification_logs(sent_at);
