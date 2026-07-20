package jwt

import (
	"encoding/base64"
	"strings"
	"testing"
	"time"

	gojwt "github.com/golang-jwt/jwt/v5"
)

// testSecret is a base64-encoded 32-byte secret (what JWT_SECRET looks like in .env).
const testSecret = "c2VjcmV0LXNlY3JldC1zZWNyZXQtc2VjcmV0LTEyMzQ=" // "secret-secret-secret-secret-1234"

func newUtil(t *testing.T, expMs int64) *JWTUtil {
	t.Helper()
	u, err := New(testSecret, expMs)
	if err != nil {
		t.Fatalf("New() error: %v", err)
	}
	return u
}

func TestNewRejectsInvalidBase64(t *testing.T) {
	if _, err := New("not-base64!!!", 3600000); err == nil {
		t.Fatal("expected error for non-base64 secret, got nil")
	}
}

// TestBase64SecretConvention proves the util signs with the base64-DECODED
// bytes of JWT_SECRET (the cross-language convention shared with the Java
// Decoders.BASE64.decode and Python base64.b64decode implementations).
func TestBase64SecretConvention(t *testing.T) {
	u := newUtil(t, 3600000)
	token, err := u.GenerateToken("alice", []string{"ADMIN"}, nil)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	rawKey, _ := base64.StdEncoding.DecodeString(testSecret)
	parsed, err := gojwt.Parse(token, func(tk *gojwt.Token) (interface{}, error) {
		return rawKey, nil
	})
	if err != nil || !parsed.Valid {
		t.Fatalf("token not verifiable with raw decoded secret bytes: %v", err)
	}

	// The raw (undecoded) secret string must NOT verify the token.
	if _, err := gojwt.Parse(token, func(tk *gojwt.Token) (interface{}, error) {
		return []byte(testSecret), nil
	}); err == nil {
		t.Fatal("token verified with the base64 string itself — secret was not decoded before signing")
	}
}

func TestGenerateAndParseRoundTrip(t *testing.T) {
	u := newUtil(t, 3600000)
	cid := int64(42)

	cases := []struct {
		name       string
		username   string
		roles      []string
		customerID *int64
		tenantID   string
	}{
		{"admin no customer", "admin", []string{"ADMIN"}, nil, ""},
		{"customer with id", "42", []string{"CUSTOMER"}, &cid, ""},
		{"multi role with tenant", "analyst", []string{"ADMIN", "ANALYST"}, nil, "nemo"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			token, err := u.GenerateTokenWithTenant(tc.username, tc.roles, tc.customerID, tc.tenantID)
			if err != nil {
				t.Fatalf("generate: %v", err)
			}
			claims, err := u.ParseToken(token)
			if err != nil {
				t.Fatalf("parse: %v", err)
			}
			if claims.Username != tc.username {
				t.Errorf("username = %q, want %q", claims.Username, tc.username)
			}
			if len(claims.Roles) != len(tc.roles) {
				t.Fatalf("roles = %v, want %v", claims.Roles, tc.roles)
			}
			for i := range tc.roles {
				if claims.Roles[i] != tc.roles[i] {
					t.Errorf("roles[%d] = %q, want %q", i, claims.Roles[i], tc.roles[i])
				}
			}
			switch {
			case tc.customerID == nil && claims.CustomerID != nil:
				t.Errorf("customerId = %v, want nil", *claims.CustomerID)
			case tc.customerID != nil && (claims.CustomerID == nil || *claims.CustomerID != *tc.customerID):
				t.Errorf("customerId = %v, want %d", claims.CustomerID, *tc.customerID)
			}
			if claims.TenantID != tc.tenantID {
				t.Errorf("tenantId = %q, want %q", claims.TenantID, tc.tenantID)
			}
		})
	}
}

func TestExtractUsername(t *testing.T) {
	u := newUtil(t, 3600000)
	token, _ := u.GenerateToken("bob", []string{"CUSTOMER"}, nil)
	name, err := u.ExtractUsername(token)
	if err != nil || name != "bob" {
		t.Fatalf("ExtractUsername = %q, %v; want bob, nil", name, err)
	}
}

func TestExtractRolesNeverNil(t *testing.T) {
	u := newUtil(t, 3600000)
	token, _ := u.GenerateToken("norole", nil, nil)
	roles, err := u.ExtractRoles(token)
	if err != nil {
		t.Fatalf("ExtractRoles: %v", err)
	}
	if roles == nil {
		t.Fatal("ExtractRoles returned nil, want empty slice")
	}
	if len(roles) != 0 {
		t.Fatalf("roles = %v, want empty", roles)
	}
}

func TestExtractCustomerID(t *testing.T) {
	u := newUtil(t, 3600000)

	cid := int64(1001)
	withID, _ := u.GenerateToken("1001", []string{"CUSTOMER"}, &cid)
	got, err := u.ExtractCustomerID(withID)
	if err != nil || got == nil || *got != cid {
		t.Fatalf("ExtractCustomerID = %v, %v; want 1001", got, err)
	}

	withoutID, _ := u.GenerateToken("admin", []string{"ADMIN"}, nil)
	got, err = u.ExtractCustomerID(withoutID)
	if err != nil {
		t.Fatalf("ExtractCustomerID: %v", err)
	}
	if got != nil {
		t.Fatalf("ExtractCustomerID = %d, want nil for admin token", *got)
	}
}

func TestParseRejectsWrongSecret(t *testing.T) {
	u := newUtil(t, 3600000)
	other, err := New(base64.StdEncoding.EncodeToString([]byte("a-completely-different-secret-32")), 3600000)
	if err != nil {
		t.Fatalf("New(other): %v", err)
	}
	token, _ := other.GenerateToken("mallory", []string{"ADMIN"}, nil)
	if _, err := u.ParseToken(token); err == nil {
		t.Fatal("expected signature validation error for token signed with a different secret")
	}
}

func TestParseRejectsExpiredToken(t *testing.T) {
	u := newUtil(t, -1000) // already expired at issue time
	token, _ := u.GenerateToken("late", []string{"CUSTOMER"}, nil)
	_, err := u.ParseToken(token)
	if err == nil {
		t.Fatal("expected expiry error")
	}
	if !strings.Contains(err.Error(), "expired") {
		t.Fatalf("error %q does not mention expiry", err)
	}
}

func TestParseRejectsNonHMACAlgorithm(t *testing.T) {
	u := newUtil(t, 3600000)
	// alg=none attack: unsigned token must be rejected.
	unsigned := gojwt.NewWithClaims(gojwt.SigningMethodNone, gojwt.MapClaims{
		"sub":   "attacker",
		"roles": []string{"ADMIN"},
		"exp":   time.Now().Add(time.Hour).Unix(),
	})
	tokenStr, err := unsigned.SignedString(gojwt.UnsafeAllowNoneSignatureType)
	if err != nil {
		t.Fatalf("building none-alg token: %v", err)
	}
	if _, err := u.ParseToken(tokenStr); err == nil {
		t.Fatal("alg=none token was accepted")
	}
}

func TestParseRejectsGarbage(t *testing.T) {
	u := newUtil(t, 3600000)
	for _, bad := range []string{"", "abc", "aaa.bbb.ccc"} {
		if _, err := u.ParseToken(bad); err == nil {
			t.Errorf("ParseToken(%q) accepted garbage", bad)
		}
	}
}
