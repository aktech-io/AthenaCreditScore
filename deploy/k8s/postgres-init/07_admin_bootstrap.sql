-- Bootstrap admin account (username: admin, password: admin — bcrypt cost 12,
-- same credentials as the docker-compose stack; nothing in the Go services
-- seeds admin_users, so a fresh database would otherwise have NO way to log in).
--
-- *** CHANGE THIS PASSWORD IMMEDIATELY on any internet-reachable deployment ***
INSERT INTO admin_users (username, password_hash, role, is_active)
VALUES ('admin', '$2b$12$l1vTxlFQgg13/rsvcaIKIu/8DWGv9Ao0fM/jgtQMne6sqKHk9/E56', 'ADMIN', true)
ON CONFLICT DO NOTHING;
