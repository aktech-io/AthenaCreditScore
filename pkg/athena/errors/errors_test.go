package errors

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func invoke(fn func(*gin.Context, string), msg string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	fn(c, msg)
	return w
}

func TestErrorHelpers(t *testing.T) {
	cases := []struct {
		name       string
		fn         func(*gin.Context, string)
		wantStatus int
		wantError  string
	}{
		{"BadRequest", BadRequest, http.StatusBadRequest, "Bad Request"},
		{"Unauthorized", Unauthorized, http.StatusUnauthorized, "Unauthorized"},
		{"Forbidden", Forbidden, http.StatusForbidden, "Forbidden"},
		{"NotFound", NotFound, http.StatusNotFound, "Not Found"},
		{"Conflict", Conflict, http.StatusConflict, "Conflict"},
		{"InternalError", InternalError, http.StatusInternalServerError, "Internal Server Error"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := invoke(tc.fn, "boom: "+tc.name)

			if w.Code != tc.wantStatus {
				t.Fatalf("HTTP status = %d, want %d", w.Code, tc.wantStatus)
			}

			var body ErrorResponse
			if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
				t.Fatalf("response is not valid JSON: %v", err)
			}
			if body.Status != tc.wantStatus {
				t.Errorf("body.status = %d, want %d", body.Status, tc.wantStatus)
			}
			if body.Error != tc.wantError {
				t.Errorf("body.error = %q, want %q", body.Error, tc.wantError)
			}
			if body.Message != "boom: "+tc.name {
				t.Errorf("body.message = %q, want %q", body.Message, "boom: "+tc.name)
			}
			if _, err := time.Parse(time.RFC3339, body.Timestamp); err != nil {
				t.Errorf("body.timestamp %q is not RFC3339: %v", body.Timestamp, err)
			}
		})
	}
}

func TestRespondCustomStatus(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/", nil)

	Respond(c, http.StatusTeapot, "Teapot", "short and stout")
	if w.Code != http.StatusTeapot {
		t.Fatalf("status = %d, want 418", w.Code)
	}
	var body ErrorResponse
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("bad JSON: %v", err)
	}
	if body.Error != "Teapot" || body.Message != "short and stout" || body.Status != 418 {
		t.Fatalf("unexpected body: %+v", body)
	}
}
