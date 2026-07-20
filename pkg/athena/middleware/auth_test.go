package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/athena/pkg/jwt"
	"github.com/gin-gonic/gin"
)

const testSecret = "c2VjcmV0LXNlY3JldC1zZWNyZXQtc2VjcmV0LTEyMzQ="

func init() {
	gin.SetMode(gin.TestMode)
}

func newJWT(t *testing.T, expMs int64) *jwt.JWTUtil {
	t.Helper()
	u, err := jwt.New(testSecret, expMs)
	if err != nil {
		t.Fatalf("jwt.New: %v", err)
	}
	return u
}

// echoRouter mounts a protected endpoint that echoes what the middleware
// stored in the context.
func echoRouter(mw gin.HandlerFunc) *gin.Engine {
	r := gin.New()
	r.GET("/protected", mw, func(c *gin.Context) {
		cid, hasCID := GetCustomerID(c)
		resp := gin.H{
			"username": GetUsername(c),
			"roles":    GetRoles(c),
			"hasCid":   hasCID,
			"cid":      cid,
		}
		if v, ok := c.Get("tenantId"); ok {
			resp["tenantId"] = v
		}
		c.JSON(http.StatusOK, resp)
	})
	return r
}

func doGet(r *gin.Engine, authHeader string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}

func TestJWTAuthRejectsMissingOrMalformedHeader(t *testing.T) {
	r := echoRouter(JWTAuth(newJWT(t, 3600000)))

	cases := []struct {
		name   string
		header string
	}{
		{"missing header", ""},
		{"not bearer", "Basic dXNlcjpwYXNz"},
		{"bearer garbage", "Bearer this.is.not-a-jwt"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if w := doGet(r, tc.header); w.Code != http.StatusUnauthorized {
				t.Fatalf("status = %d, want 401", w.Code)
			}
		})
	}
}

func TestJWTAuthAcceptsValidTokenAndSetsClaims(t *testing.T) {
	u := newJWT(t, 3600000)
	r := echoRouter(JWTAuth(u))

	cid := int64(7)
	token, err := u.GenerateTokenWithTenant("7", []string{"CUSTOMER"}, &cid, "nemo")
	if err != nil {
		t.Fatalf("generate: %v", err)
	}

	w := doGet(r, "Bearer "+token)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body=%s", w.Code, w.Body.String())
	}
	var body struct {
		Username string   `json:"username"`
		Roles    []string `json:"roles"`
		HasCid   bool     `json:"hasCid"`
		Cid      int64    `json:"cid"`
		TenantID string   `json:"tenantId"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("bad JSON: %v", err)
	}
	if body.Username != "7" {
		t.Errorf("username = %q, want 7", body.Username)
	}
	if len(body.Roles) != 1 || body.Roles[0] != "CUSTOMER" {
		t.Errorf("roles = %v, want [CUSTOMER]", body.Roles)
	}
	if !body.HasCid || body.Cid != 7 {
		t.Errorf("customerId = (%v,%d), want (true,7)", body.HasCid, body.Cid)
	}
	if body.TenantID != "nemo" {
		t.Errorf("tenantId = %q, want nemo", body.TenantID)
	}
}

func TestJWTAuthExpiredTokenMessage(t *testing.T) {
	expired := newJWT(t, -1000)
	token, _ := expired.GenerateToken("late", []string{"CUSTOMER"}, nil)

	r := echoRouter(JWTAuth(newJWT(t, 3600000)))
	w := doGet(r, "Bearer "+token)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", w.Code)
	}
	var body map[string]string
	_ = json.Unmarshal(w.Body.Bytes(), &body)
	if body["error"] != "Token expired" {
		t.Errorf("error = %q, want \"Token expired\"", body["error"])
	}
}

func TestOptionalJWTAuth(t *testing.T) {
	u := newJWT(t, 3600000)
	r := echoRouter(OptionalJWTAuth(u))

	// No header: request still passes, defaults apply.
	w := doGet(r, "")
	if w.Code != http.StatusOK {
		t.Fatalf("anonymous status = %d, want 200", w.Code)
	}
	var anon map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &anon)
	if anon["username"] != "system" {
		t.Errorf("anonymous username = %v, want system (GetUsername default)", anon["username"])
	}
	if anon["hasCid"] != false {
		t.Errorf("anonymous hasCid = %v, want false", anon["hasCid"])
	}

	// Invalid token: ignored, not rejected.
	if w := doGet(r, "Bearer junk"); w.Code != http.StatusOK {
		t.Fatalf("invalid-token status = %d, want 200 for optional auth", w.Code)
	}

	// Valid token: claims populated.
	token, _ := u.GenerateToken("carol", []string{"ANALYST"}, nil)
	w = doGet(r, "Bearer "+token)
	var body map[string]interface{}
	_ = json.Unmarshal(w.Body.Bytes(), &body)
	if body["username"] != "carol" {
		t.Errorf("username = %v, want carol", body["username"])
	}
}
