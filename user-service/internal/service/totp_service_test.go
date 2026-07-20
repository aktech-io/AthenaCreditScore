package service

import (
	"strings"
	"testing"
	"time"
)

// RFC 6238 Appendix B test vectors (SHA-1). The RFC lists 8-digit codes for
// the 20-byte ASCII secret "12345678901234567890"; our 6-digit codes are the
// last 6 digits of each vector.
const rfcSecret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ" // base32("12345678901234567890")

func TestValidateTOTPRFCVectors(t *testing.T) {
	vectors := []struct {
		unix int64
		code string // last 6 of the RFC 8-digit value
	}{
		{59, "287082"},          // 94287082
		{1111111109, "081804"},  // 07081804
		{1111111111, "050471"},  // 14050471
		{1234567890, "005924"},  // 89005924
		{2000000000, "279037"},  // 69279037
	}
	for _, v := range vectors {
		if !ValidateTOTP(rfcSecret, v.code, time.Unix(v.unix, 0).UTC()) {
			t.Errorf("RFC vector at t=%d: code %s should validate", v.unix, v.code)
		}
	}
}

func TestValidateTOTPSkew(t *testing.T) {
	at := time.Unix(1111111109, 0).UTC()
	// The code for the previous 30s step must still validate (±1 skew)…
	if !ValidateTOTP(rfcSecret, "081804", at.Add(30*time.Second)) {
		t.Error("code from previous step should validate within skew")
	}
	// …but a code from two steps away must not.
	if ValidateTOTP(rfcSecret, "081804", at.Add(90*time.Second)) {
		t.Error("code two steps away must not validate")
	}
}

func TestValidateTOTPRejects(t *testing.T) {
	at := time.Unix(59, 0).UTC()
	if ValidateTOTP(rfcSecret, "000000", at) {
		t.Error("wrong code must not validate")
	}
	if ValidateTOTP(rfcSecret, "28708", at) {
		t.Error("short code must not validate")
	}
	if ValidateTOTP("not-base32!!", "287082", at) {
		t.Error("invalid secret must not validate")
	}
	if ValidateTOTP("", "287082", at) {
		t.Error("empty secret must not validate")
	}
}

func TestGenerateTOTPSecret(t *testing.T) {
	a, err := GenerateTOTPSecret()
	if err != nil {
		t.Fatalf("generate: %v", err)
	}
	b, _ := GenerateTOTPSecret()
	if a == b {
		t.Error("secrets must be unique")
	}
	if len(a) != 32 { // 20 bytes → 32 base32 chars unpadded
		t.Errorf("unexpected secret length %d", len(a))
	}
	if strings.Contains(a, "=") {
		t.Error("secret must be unpadded base32")
	}
}

func TestProvisioningURI(t *testing.T) {
	uri := TOTPProvisioningURI("admin", "ABC234")
	for _, want := range []string{"otpauth://totp/", "NemoScore:admin", "secret=ABC234", "digits=6", "period=30"} {
		if !strings.Contains(uri, want) {
			t.Errorf("URI %q missing %q", uri, want)
		}
	}
}
