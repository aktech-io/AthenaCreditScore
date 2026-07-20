package service

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha1"
	"crypto/subtle"
	"encoding/base32"
	"encoding/binary"
	"fmt"
	"net/url"
	"strings"
	"time"
)

// TOTP (RFC 6238) implemented on the standard library — SHA-1, 6 digits,
// 30-second period, ±1 step clock skew — the parameters Google Authenticator,
// Authy, and 1Password all default to. Kept dependency-free on purpose: the
// whole algorithm is HMAC over a counter.

const (
	totpPeriod  = 30 * time.Second
	totpDigits  = 6
	totpSkew    = 1 // accept previous/next step for clock drift
	totpKeyLen  = 20
	totpIssuer  = "NemoScore"
)

// GenerateTOTPSecret returns a new base32 (unpadded) shared secret.
func GenerateTOTPSecret() (string, error) {
	key := make([]byte, totpKeyLen)
	if _, err := rand.Read(key); err != nil {
		return "", fmt.Errorf("totp secret generation: %w", err)
	}
	return base32.StdEncoding.WithPadding(base32.NoPadding).EncodeToString(key), nil
}

// TOTPProvisioningURI renders the otpauth:// URI encoded by enrollment QR codes.
func TOTPProvisioningURI(account, secret string) string {
	return fmt.Sprintf(
		"otpauth://totp/%s:%s?secret=%s&issuer=%s&algorithm=SHA1&digits=%d&period=%d",
		totpIssuer, url.PathEscape(account), secret, totpIssuer, totpDigits, int(totpPeriod.Seconds()),
	)
}

func hotp(key []byte, counter uint64) string {
	var buf [8]byte
	binary.BigEndian.PutUint64(buf[:], counter)
	mac := hmac.New(sha1.New, key)
	mac.Write(buf[:])
	sum := mac.Sum(nil)
	offset := sum[len(sum)-1] & 0x0f
	code := (binary.BigEndian.Uint32(sum[offset:offset+4]) & 0x7fffffff) % 1_000_000
	return fmt.Sprintf("%06d", code)
}

// ValidateTOTP checks a 6-digit code against the shared secret at the given
// time, tolerating ±totpSkew steps. Constant-time code comparison.
func ValidateTOTP(secret, code string, at time.Time) bool {
	normalized := strings.ToUpper(strings.ReplaceAll(strings.TrimSpace(secret), " ", ""))
	key, err := base32.StdEncoding.WithPadding(base32.NoPadding).DecodeString(strings.TrimRight(normalized, "="))
	if err != nil {
		return false
	}
	code = strings.TrimSpace(code)
	if len(code) != totpDigits {
		return false
	}
	counter := uint64(at.Unix()) / uint64(totpPeriod.Seconds())
	for i := -totpSkew; i <= totpSkew; i++ {
		expected := hotp(key, uint64(int64(counter)+int64(i)))
		if subtle.ConstantTimeCompare([]byte(expected), []byte(code)) == 1 {
			return true
		}
	}
	return false
}
