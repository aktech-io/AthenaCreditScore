-- Admin TOTP enrollment (NemoScore Phase 5).
-- totp_secret existed but was never enforced; totp_pending_secret holds the
-- generated-but-unconfirmed secret during enrollment (becomes totp_secret
-- once the admin proves possession with a valid code).
--
-- Apply by hand to already-initialized DBs (initdb won't rerun):
--   docker exec -i athena-postgres psql -U athena -d athena_db < database/migrations/2026_07_admin_totp.sql
-- and to the live Contabo nemoscore postgres. Also mirrored in schema.sql.

ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS totp_pending_secret VARCHAR(100);
