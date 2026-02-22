-- V1: User management schema (roles, groups, users, invitations, password policies)
-- Note: admin_users table is managed externally (pre-existing seed data).

CREATE TABLE IF NOT EXISTS roles (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS user_groups (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS group_roles (
    group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    role_id  BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, role_id)
);

CREATE TABLE IF NOT EXISTS users (
    id         BIGSERIAL PRIMARY KEY,
    username   VARCHAR(255) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name  VARCHAR(100),
    email      VARCHAR(255),
    status     VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS user_group_members (
    user_id  BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS invitations (
    id          BIGSERIAL PRIMARY KEY,
    token       VARCHAR(255) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL,
    expiry_date TIMESTAMP    NOT NULL,
    used        BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS invitation_roles (
    invitation_id BIGINT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
    role_id       BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (invitation_id, role_id)
);

CREATE TABLE IF NOT EXISTS invitation_groups (
    invitation_id BIGINT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
    group_id      BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (invitation_id, group_id)
);

CREATE TABLE IF NOT EXISTS password_policies (
    id                   BIGSERIAL PRIMARY KEY,
    min_length           INTEGER NOT NULL DEFAULT 8,
    require_uppercase    BOOLEAN NOT NULL DEFAULT TRUE,
    require_lowercase    BOOLEAN NOT NULL DEFAULT TRUE,
    require_numbers      BOOLEAN NOT NULL DEFAULT TRUE,
    require_special_chars BOOLEAN NOT NULL DEFAULT FALSE,
    expiration_days      INTEGER NOT NULL DEFAULT 90,
    special_chars        VARCHAR(100)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_username   ON users(username);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
