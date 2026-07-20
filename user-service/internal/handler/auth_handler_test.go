package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/athena/pkg/jwt"
	"github.com/athena/user-service/internal/repository"
	"github.com/glebarez/sqlite"
	"github.com/gin-gonic/gin"
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
func newAuthRig(t *testing.T) (*gin.Engine, *jwt.JWTUtil) {
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
		is_active BOOLEAN NOT NULL DEFAULT 1)`).Error; err != nil {
		t.Fatalf("create admin_users: %v", err)
	}
	if err := db.Exec(`CREATE TABLE customers (
		customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
		first_name TEXT, last_name TEXT,
		mobile_number TEXT, email TEXT)`).Error; err != nil {
		t.Fatalf("create customers: %v", err)
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

	h := NewAuthHandler(repository.NewAdminUserRepository(db), jwtUtil, nil, db)
	r := gin.New()
	h.RegisterRoutes(r.Group("/api/auth"))
	return r, jwtUtil
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
	r, jwtUtil := newAuthRig(t)

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

func TestVerifyOTP(t *testing.T) {
	r, jwtUtil := newAuthRig(t)

	t.Run("wrong OTP rejected", func(t *testing.T) {
		w := postJSON(r, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=999999", nil)
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})

	t.Run("known phone gets customerId claim", func(t *testing.T) {
		w := postJSON(r, "/api/auth/customer/verify-otp?phone=%2B254700000001&otp=123456", nil)
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
		claims, err := jwtUtil.ParseToken(resp.Token)
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
}

func TestDemoToken(t *testing.T) {
	r, jwtUtil := newAuthRig(t)

	t.Run("missing customerId", func(t *testing.T) {
		if w := postJSON(r, "/api/auth/customer/demo-token", nil); w.Code != http.StatusBadRequest {
			t.Fatalf("status = %d, want 400", w.Code)
		}
	})

	t.Run("issues customer token", func(t *testing.T) {
		w := postJSON(r, "/api/auth/customer/demo-token?customerId=55", nil)
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200", w.Code)
		}
		var resp struct {
			Token string `json:"token"`
		}
		_ = json.Unmarshal(w.Body.Bytes(), &resp)
		claims, err := jwtUtil.ParseToken(resp.Token)
		if err != nil {
			t.Fatalf("token does not verify: %v", err)
		}
		if claims.CustomerID == nil || *claims.CustomerID != 55 {
			t.Errorf("token customerId = %v, want 55", claims.CustomerID)
		}
	})
}

func TestPortalLogin(t *testing.T) {
	r, jwtUtil := newAuthRig(t)

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

	// KNOWN INSECURE — this asserts current behavior, not intended behavior.
	// The customer branch of /api/auth/login issues a CUSTOMER JWT on a phone/email
	// lookup alone, without checking the password, so any known mobile number is a
	// full account login. Customers are supposed to authenticate via the OTP flow.
	// Do not treat this passing test as a sign the endpoint is safe; when the
	// endpoint is fixed, this expectation must be inverted to expect 401.
	t.Run("customer by phone gets tenant-scoped token", func(t *testing.T) {
		w := postJSON(r, "/api/auth/login", map[string]string{"username": "+254700000001", "password": "anything"})
		if w.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200 (body=%s)", w.Code, w.Body.String())
		}
		var resp struct {
			Token string `json:"token"`
			User  struct {
				Role       string `json:"role"`
				CustomerID string `json:"customerId"`
			} `json:"user"`
		}
		_ = json.Unmarshal(w.Body.Bytes(), &resp)
		if resp.User.Role != "CUSTOMER" || resp.User.CustomerID != "1001" {
			t.Errorf("user = %+v, want CUSTOMER/1001", resp.User)
		}
		claims, err := jwtUtil.ParseToken(resp.Token)
		if err != nil {
			t.Fatalf("token does not verify: %v", err)
		}
		if claims.CustomerID == nil || *claims.CustomerID != 1001 {
			t.Errorf("token customerId = %v, want 1001", claims.CustomerID)
		}
		if claims.TenantID == "" {
			t.Error("customer portal token missing tenantId claim")
		}
	})

	t.Run("unknown identity rejected", func(t *testing.T) {
		w := postJSON(r, "/api/auth/login", map[string]string{"username": "nobody@nowhere", "password": "x"})
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want 401", w.Code)
		}
	})
}
