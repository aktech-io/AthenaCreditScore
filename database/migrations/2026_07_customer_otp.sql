-- Customer OTP storage for the portal sign-in flow.
--
-- Customers have no password (the customers table carries no credential column);
-- they authenticate with a one-time code sent to their registered mobile number.
-- Only the bcrypt hash of the code is stored, never the code itself.

CREATE TABLE IF NOT EXISTS customer_otps (
    id          BIGSERIAL PRIMARY KEY,
    phone       VARCHAR(20)  NOT NULL,
    otp_hash    VARCHAR(100) NOT NULL,
    expires_at  TIMESTAMPTZ  NOT NULL,
    attempts    SMALLINT     NOT NULL DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Verify looks up the newest unconsumed code for a phone; Issue counts recent
-- codes per phone to throttle. Both are served by this index.
CREATE INDEX IF NOT EXISTS idx_customer_otps_phone_created
    ON customer_otps (phone, created_at DESC);
