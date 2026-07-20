package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// rolesRouter injects the given roles into the context (as JWTAuth would)
// then applies RequireRoles.
func rolesRouter(userRoles []string, required ...string) *gin.Engine {
	r := gin.New()
	inject := func(c *gin.Context) {
		if userRoles != nil {
			c.Set("roles", userRoles)
		}
		c.Next()
	}
	r.GET("/admin", inject, RequireRoles(required...), func(c *gin.Context) {
		c.String(http.StatusOK, "ok")
	})
	return r
}

func TestRequireRoles(t *testing.T) {
	cases := []struct {
		name       string
		userRoles  []string
		required   []string
		wantStatus int
	}{
		{"exact match", []string{"ADMIN"}, []string{"ADMIN"}, http.StatusOK},
		{"one of many", []string{"ANALYST"}, []string{"ADMIN", "ANALYST"}, http.StatusOK},
		{"extra user roles", []string{"CUSTOMER", "ADMIN"}, []string{"ADMIN"}, http.StatusOK},
		{"wrong role", []string{"CUSTOMER"}, []string{"ADMIN"}, http.StatusForbidden},
		{"no roles in context", nil, []string{"ADMIN"}, http.StatusForbidden},
		{"empty roles slice", []string{}, []string{"ADMIN"}, http.StatusForbidden},
		{"case sensitive", []string{"admin"}, []string{"ADMIN"}, http.StatusForbidden},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := rolesRouter(tc.userRoles, tc.required...)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/admin", nil))
			if w.Code != tc.wantStatus {
				t.Fatalf("status = %d, want %d", w.Code, tc.wantStatus)
			}
		})
	}
}
