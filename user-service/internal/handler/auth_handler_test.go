package handler

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha1"
	"encoding/base32"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/athena/pkg/jwt"
	"github.com/athena/user-service/internal/repository"
	"github.com/athena/user-service/internal/service"
	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

const testSecret = "c2VjcmV0LXNlY3JldC1zZWNyZXQtc2VjcmV0LTEyMzQ="

func init() {
	gin.SetMode(gin.TestMode)
}

// newAuthRig builds an AuthHandler backed by an in-memory sqlite DB seeded
// with one admin ("admin"/"admin123", role ADMIN) and one customer
// (id 1001, phone +254700000001).
func newAuthRig(t *testing.T) *authRig {
	t.Helper()

	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{Logger: logger.Default.LogMode(logger.Silent)})
	if err != nil {
		t.Fatalf("open sqlite: %v", err)
	}

	if err := db.Exec(`CREATE TABLE admin_users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT NOT NULL UNIQUE,
		password_hash TEXT NOT NULL,
		first_name TEXT, last_name TEXT, email TEXT,
		role TEXT NOT NULL,
		totp_secret TEXT,
		totp_pending_secret TEXT,
		is_active BOOLEAN NOT NULL DEFAULT 1)`).Error; err != nil {
		t.Fatalf("create admin_users: %v", err)
	}
	if err := db.Exec(`CREATE TABLE customers (
		customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
		first_name TEXT, last_name TEXT,
		mobile_number TEXT, email TEXT)`).Error; err != nil {
		t.Fatalf("create customers: %v", err)
	}
	if err := db.Exec(`CREATE TABLE customer_otps (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		phone TEXT NOT NULL,
		otp_hash TEXT NOT NULL,
		expires_at DATETIME NOT NULL,
		attempts SMALLINT NOT NULL DEFAULT 0,
		consumed_at DATETIME,
		created_at DATETIME NOT NULL)`).Error; err != nil {
		t.Fatalf("create customer_otps: %v", err)
	}

	hash, _ := bcrypt.GenerateFromPassword([]byte("admin123"), bcrypt.MinCost)
	if err := db.Exec(
		"INSERT INTO admin_users (username, password_hash, role) VALUES (?,?,?)",
		"admin", string(hash), "ADMIN",
	).Error; err != nil {
		t.Fatalf("seed admin: %v", err)
	}
	if err := db.Exec(
		"INSERT INTO customers (customer_id, first_name, last_name, mobile_number, email) VALUES (1001,'Wanjiku','Kamau','+254700000001','wanjiku@example.com')",
	).Error; err != nil {
		t.Fatalf("seed customer: %v", err)
	}

	jwtUtil, err := jwt.New(testSecret, 3600000)
	if err != nil {
		t.Fatalf("jwt.New: %v", err)
	}

	otpSvc := service.NewOTPService(db)
	h := NewAuthHandler(repository.NewAdminUserRepository(db), jwtUtil, nil, otpSvc, nil, db)
	r := gin.New()
	h.RegisterRoutes(r.Group("/api/auth"))
	return &authRig{engine: r, jwt: jwtUtil, db: db, otp: otpSvc}
}

// authRig bundles the pieces a test needs. The OTP service is exposed because the
// plaintext code is never stored — only its bcrypt hash — so a test that needs a
// valid code has to obtain it from the issuing call itself.
type authRig struct {
	engine *gin.Engine
	jwt    *jwt.JWTUtil
	db     *gorm.DB
	otp    *service.OTPService
}

func postJSON(r *gin.Engine, path string, body interface{}) *httptest.ResponseRecorder {
	var buf bytes.Buffer
	if body != nil {
		_ = json.NewEncoder(&buf).Encode(body)
	}
	req := httptest.NewRequest(http.MethodPost, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}

func TestAdminLogin(t *testing.T) {
	rig := newAuthRig(t)
	r, jwtUtil := rig.engine, rig.jwt

	cases := []struct {
		name       string
		body       interface{}
		wantStatus int
	}{
		{"success", map[string]string{"username": "admin", "password": "admin123"}, http.StatusOK},
		{"wrong password", map[string]string{"username": "admin", "password": "nope"}, http.StatusUnauthorized},
		{"unknown user", map[string]string{"username": "ghost", "password": "admin123"}, http.StatusUnauthorized},
		{"missing password", map[string]string{"username": "admin"}, http.StatusBadRequest},
		{"empty body", nil, http.StatusBadRequest},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := postJSON(r, "/api/auth/admin/login", tc.body)
			if w.Code != tc.wantStatus {
				t.Fatalf("status = %d, want %d (body=%s)", w.Code, tc.wantStatus, w.Body.String())
			}
			if tc.wantStatus != http.StatusOK {
				return
			}
			var resp struct {
				Token string   `json:"token"`
				Roles []string `json:"roles"`
			}
			if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
				t.Fatalf("bad JSON: %v", err)
			}
			claims, err := jwtUtil.ParseToken(resp.Token)
			if err != nil {
				t.Fatalf("issued token does not verify: %v", err)
			}
			if claims.Username != "admin" {
				t.Errorf("token sub = %q, want admin", claims.Username)
			}
			if len(claims.Roles) != 1 || claims.Roles[0] != "ADMIN" {
				t.Errorf("token roles = %v, want [ADMIN]", claims.Roles)
			}
			if claims.CustomerID != nil {
				t.Error("admin token unexpectedly carries a customerId claim")
			}
		})
	}
}

const testPhone = "+254700000001"

func TestRequestOTP(t *testing.T) {
	rig := newAuthRig(t)

	t.Run("missing phone", func(t *testing.T) {
		if w := postJSON(rig.engine, "/api/auth/customer/request-otp", nil); w.Code != http.StatusBadRequest {
			t.Fatalf("status = %d, want 400", w.Code)
		}
	})

	// An unregistered number must be indistinguishable from a registered one, or
	// the endpoint becomes a customer-enumeration oracle.
	t.Run("unknown number is indistinguishable", func(t *testing.T) {
		known := postJSON(rig.engine, "/api/auth/customer/request-otp?phone="+url.QueryEscape(testPhone), nil)
		unknown := postJSON(rig.engine, "/api/auth/customer/request-otp?phone=%2B254799999999", nil)
		if known.Code != unknown.Code || known.Body.String() != unknown.Body.String() {
			t.Errorf("responses differ: known=%d/%s unknown=%d/%s",
				known.Code, known.Body.String(), unknown.Code, unknown.Body.String())
		}
		var stored int64
		rig.db.Raw("SELECT COUNT(*) FROM customer_otps WHERE phone = ?", "+254799999999").Scan(&stored)
		if stored != 0 {
			t.Errorf("stored %d codes for an unregistered number, want 0", stored)
		}
	})

	t.Run("throttles repeated requests", func(t *testing.T) {
		rig := newAuthRig(t)
		var lastCode int
		for i := 0; i < 5; i++ {
			w := postJSON(rig.engine, "/api/auth/customer/request-otp?phone="+url.QueryEscape(testPhone), nil)
			lastCode = w.Code
		}
		if lastCode != http.StatusTooManyRequests {
			t.Errorf("status after 5 requests = %d, want 429", lastCode)
		}
	})
}

func TestVerifyOTP(t *testing.T) {
	t.Run("wrong code rejected", func(t *testing.T) {
		rig := newAuthRig(t)
		if _, err := rig.otp.Issue(testPhone); err != nil {
			t.Fatalf("issue: %v", err)
		}
		w := postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=999999", nil)
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})

	t.Run("no outstanding code rejected", func(t *testing.T) {
		rig := newAuthRig(t)
		w := postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=123456", nil)
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})

	// The old implementation accepted the literal "123456" for any phone.
	t.Run("hardcoded 123456 is not accepted", func(t *testing.T) {
		rig := newAuthRig(t)
		code, err := rig.otp.Issue(testPhone)
		if err != nil {
			t.Fatalf("issue: %v", err)
		}
		if code == "123456" {
			t.Skip("issued code happens to be 123456")
		}
		w := postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=123456", nil)
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})

	t.Run("valid code gets customerId claim", func(t *testing.T) {
		rig := newAuthRig(t)
		code, err := rig.otp.Issue(testPhone)
		if err != nil {
			t.Fatalf("issue: %v", err)
		}
		w := postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp="+code, nil)
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200 (body=%s)", w.Code, w.Body.String())
		}
		var resp struct {
			Token      string `json:"token"`
			CustomerID *int64 `json:"customerId"`
		}
		_ = json.Unmarshal(w.Body.Bytes(), &resp)
		if resp.CustomerID == nil || *resp.CustomerID != 1001 {
			t.Fatalf("customerId = %v, want 1001", resp.CustomerID)
		}
		claims, err := rig.jwt.ParseToken(resp.Token)
		if err != nil {
			t.Fatalf("token does not verify: %v", err)
		}
		if claims.CustomerID == nil || *claims.CustomerID != 1001 {
			t.Errorf("token customerId = %v, want 1001", claims.CustomerID)
		}
		if len(claims.Roles) != 1 || claims.Roles[0] != "CUSTOMER" {
			t.Errorf("token roles = %v, want [CUSTOMER]", claims.Roles)
		}
	})

	t.Run("code is single use", func(t *testing.T) {
		rig := newAuthRig(t)
		code, err := rig.otp.Issue(testPhone)
		if err != nil {
			t.Fatalf("issue: %v", err)
		}
		path := "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=" + code
		if w := postJSON(rig.engine, path, nil); w.Code != http.StatusOK {
			t.Fatalf("first use status = %d, want 200", w.Code)
		}
		if w := postJSON(rig.engine, path, nil); w.Code != http.StatusUnauthorized {
			t.Errorf("replay status = %d, want 401", w.Code)
		}
	})

	t.Run("guessing burns the attempt budget", func(t *testing.T) {
		rig := newAuthRig(t)
		code, err := rig.otp.Issue(testPhone)
		if err != nil {
			t.Fatalf("issue: %v", err)
		}
		for i := 0; i < 5; i++ {
			postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=000001", nil)
		}
		// The real code must no longer work once the budget is exhausted.
		w := postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp="+code, nil)
		if w.Code != http.StatusUnauthorized {
			t.Errorf("status after 5 failures = %d, want 401", w.Code)
		}
	})

	t.Run("expired code rejected", func(t *testing.T) {
		rig := newAuthRig(t)
		code, err := rig.otp.Issue(testPhone)
		if err != nil {
			t.Fatalf("issue: %v", err)
		}
		if err := rig.db.Exec(
			"UPDATE customer_otps SET expires_at = ? WHERE phone = ?",
			time.Now().Add(-time.Minute), testPhone,
		).Error; err != nil {
			t.Fatalf("expire: %v", err)
		}
		w := postJSON(rig.engine, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp="+code, nil)
		if w.Code != http.StatusUnauthorized {
			t.Errorf("status = %d, want 401", w.Code)
		}
	})
}

func TestDemoToken(t *testing.T) {
	rig := newAuthRig(t)

	// The route mints a token for any customerId with no authentication, so it must
	// stay off unless deliberately enabled. This is the default-deployment case.
	t.Run("disabled by default", func(t *testing.T) {
		if w := postJSON(rig.engine, "/api/auth/customer/demo-token?customerId=55", nil); w.Code != http.StatusNotFound {
			t.Fatalf("status = %d, want 404 (body=%s)", w.Code, w.Body.String())
		}
	})

	t.Run("enabled by ALLOW_DEMO_TOKENS", func(t *testing.T) {
		t.Setenv("ALLOW_DEMO_TOKENS", "true")

		if w := postJSON(rig.engine, "/api/auth/customer/demo-token", nil); w.Code != http.StatusBadRequest {
			t.Fatalf("missing customerId status = %d, want 400", w.Code)
		}

		w := postJSON(rig.engine, "/api/auth/customer/demo-token?customerId=55", nil)
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200", w.Code)
		}
		var resp struct {
			Token string `json:"token"`
		}
		_ = json.Unmarshal(w.Body.Bytes(), &resp)
		claims, err := rig.jwt.ParseToken(resp.Token)
		if err != nil {
			t.Fatalf("token does not verify: %v", err)
		}
		if claims.CustomerID == nil || *claims.CustomerID != 55 {
			t.Errorf("token customerId = %v, want 55", claims.CustomerID)
		}
	})
}

func TestPortalLogin(t *testing.T) {
	rig := newAuthRig(t)
	r, jwtUtil := rig.engine, rig.jwt

	t.Run("admin credentials", func(t *testing.T) {
		w := postJSON(r, "/api/auth/login", map[string]string{"username": "admin", "password": "admin123"})
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200 (body=%s)", w.Code, w.Body.String())
		}
		var resp struct {
			Token string `json:"token"`
			User  struct {
				Role string `json:"role"`
			} `json:"user"`
		}
		_ = json.Unmarshal(w.Body.Bytes(), &resp)
		if resp.User.Role != "ADMIN" {
			t.Errorf("user.role = %q, want ADMIN", resp.User.Role)
		}
		if _, err := jwtUtil.ParseToken(resp.Token); err != nil {
			t.Errorf("token does not verify: %v", err)
		}
	})

	// This endpoint used to issue a CUSTOMER token on a phone/email match alone,
	// with no credential check, making any known mobile number a full account
	// login. It must never hand out a customer token again.
	t.Run("known customer phone is not a login", func(t *testing.T) {
		for _, identity := range []string{"+254700000001", "wanjiku@example.com"} {
			w := postJSON(r, "/api/auth/login", map[string]string{"username": identity, "password": "anything"})
			if w.Code != http.StatusUnauthorized {
				t.Errorf("%s: status = %d, want 401 (body=%s)", identity, w.Code, w.Body.String())
			}
			if bytes.Contains(w.Body.Bytes(), []byte("token")) {
				t.Errorf("%s: response carries a token: %s", identity, w.Body.String())
			}
		}
	})

	t.Run("unknown identity rejected", func(t *testing.T) {
		w := postJSON(r, "/api/auth/login", map[string]string{"username": "nobody@nowhere", "password": "x"})
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})
}

// totpCodeAt regenerates a live TOTP code for tests (RFC 6238, SHA-1,
// 6 digits, 30s period) — mirrors the service implementation.
func totpCodeAt(secret string, at time.Time) string {
	key, _ := base32.StdEncoding.WithPadding(base32.NoPadding).DecodeString(secret)
	counter := uint64(at.Unix()) / 30
	var buf [8]byte
	binary.BigEndian.PutUint64(buf[:], counter)
	mac := hmac.New(sha1.New, key)
	mac.Write(buf[:])
	sum := mac.Sum(nil)
	offset := sum[len(sum)-1] & 0x0f
	code := (binary.BigEndian.Uint32(sum[offset:offset+4]) & 0x7fffffff) % 1_000_000
	return fmt.Sprintf("%06d", code)
}

func TestAdminLoginTotpEnforced(t *testing.T) {
	rig := newAuthRig(t)

	secret, err := service.GenerateTOTPSecret()
	if err != nil {
		t.Fatalf("generate secret: %v", err)
	}
	hash, _ := bcrypt.GenerateFromPassword([]byte("mfa-pass"), bcrypt.MinCost)
	if err := rig.db.Exec(
		"INSERT INTO admin_users (username, password_hash, role, totp_secret) VALUES (?,?,?,?)",
		"mfa-admin", string(hash), "ADMIN", secret,
	).Error; err != nil {
		t.Fatalf("seed mfa admin: %v", err)
	}

	t.Run("password alone is rejected with totpRequired", func(t *testing.T) {
		w := postJSON(rig.engine, "/api/auth/admin/login",
			map[string]string{"username": "mfa-admin", "password": "mfa-pass"})
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401 (body=%s)", w.Code, w.Body.String())
		}
		var resp map[string]interface{}
		_ = json.Unmarshal(w.Body.Bytes(), &resp)
		if resp["totpRequired"] != true {
			t.Fatalf("expected totpRequired=true, body=%s", w.Body.String())
		}
	})

	t.Run("wrong code is rejected", func(t *testing.T) {
		w := postJSON(rig.engine, "/api/auth/admin/login",
			map[string]string{"username": "mfa-admin", "password": "mfa-pass", "totpCode": "000000"})
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})

	t.Run("valid code logs in", func(t *testing.T) {
		w := postJSON(rig.engine, "/api/auth/admin/login",
			map[string]string{"username": "mfa-admin", "password": "mfa-pass",
				"totpCode": totpCodeAt(secret, time.Now())})
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200 (body=%s)", w.Code, w.Body.String())
		}
	})

	t.Run("portal login enforces the same second factor", func(t *testing.T) {
		w := postJSON(rig.engine, "/api/auth/login",
			map[string]string{"username": "mfa-admin", "password": "mfa-pass"})
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
		w = postJSON(rig.engine, "/api/auth/login",
			map[string]string{"username": "mfa-admin", "password": "mfa-pass",
				"totpCode": totpCodeAt(secret, time.Now())})
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200 (body=%s)", w.Code, w.Body.String())
		}
	})

	t.Run("admins without TOTP are unaffected", func(t *testing.T) {
		w := postJSON(rig.engine, "/api/auth/admin/login",
			map[string]string{"username": "admin", "password": "admin123"})
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200 (body=%s)", w.Code, w.Body.String())
		}
	})
}
