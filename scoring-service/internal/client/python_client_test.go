package client

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

type recorded struct {
	method string
	path   string
	header http.Header
}

// stubPython spins up an httptest server that records the last request and
// replies with the given status/body.
func stubPython(t *testing.T, status int, body interface{}) (*httptest.Server, *recorded) {
	t.Helper()
	rec := &recorded{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		rec.method = r.Method
		rec.path = r.URL.Path
		rec.header = r.Header.Clone()
		w.WriteHeader(status)
		if body != nil {
			_ = json.NewEncoder(w).Encode(body)
		}
	}))
	t.Cleanup(srv.Close)
	return srv, rec
}

func TestGetCreditScoreForwardsAuthAndParses(t *testing.T) {
	srv, rec := stubPython(t, http.StatusOK, map[string]interface{}{
		"customer_id": 1, "final_score": 715, "score_band": "Good", "status": "SCORED",
	})
	c := NewPythonClient(srv.URL)

	got, err := c.GetCreditScore(1, "Bearer abc123")
	if err != nil {
		t.Fatalf("GetCreditScore: %v", err)
	}
	if rec.method != http.MethodGet || rec.path != "/api/v1/credit-score/1" {
		t.Errorf("request = %s %s, want GET /api/v1/credit-score/1", rec.method, rec.path)
	}
	if rec.header.Get("Authorization") != "Bearer abc123" {
		t.Errorf("Authorization = %q, want forwarded bearer", rec.header.Get("Authorization"))
	}
	if got["final_score"].(float64) != 715 {
		t.Errorf("final_score = %v, want 715", got["final_score"])
	}
}

func TestGetCreditReportPath(t *testing.T) {
	srv, rec := stubPython(t, http.StatusOK, map[string]interface{}{"customer_id": 9})
	c := NewPythonClient(srv.URL)

	if _, err := c.GetCreditReport(9, ""); err != nil {
		t.Fatalf("GetCreditReport: %v", err)
	}
	if rec.path != "/api/v1/credit-report/9" {
		t.Errorf("path = %q, want /api/v1/credit-report/9", rec.path)
	}
	if _, ok := rec.header["Authorization"]; ok {
		t.Error("Authorization header sent despite empty authHeader")
	}
}

func TestGetCreditScoreByAPIKeyDefaultsToDevKey(t *testing.T) {
	t.Setenv("SCORING_ENGINE_API_KEY", "")
	srv, rec := stubPython(t, http.StatusOK, map[string]interface{}{"ok": true})
	c := NewPythonClient(srv.URL)

	if _, err := c.GetCreditScoreByAPIKey(3); err != nil {
		t.Fatalf("GetCreditScoreByAPIKey: %v", err)
	}
	if got := rec.header.Get("X-Api-Key"); got != "dev-key" {
		t.Errorf("X-Api-Key = %q, want dev-key fallback", got)
	}
}

func TestScoringEngineAPIKeyEnvOverride(t *testing.T) {
	t.Setenv("SCORING_ENGINE_API_KEY", "prod-secret-key")
	srv, rec := stubPython(t, http.StatusOK, map[string]interface{}{"ok": true})
	c := NewPythonClient(srv.URL) // key is read at construction time

	if _, err := c.GetCreditScoreByAPIKey(3); err != nil {
		t.Fatalf("GetCreditScoreByAPIKey: %v", err)
	}
	if got := rec.header.Get("X-Api-Key"); got != "prod-secret-key" {
		t.Errorf("X-Api-Key = %q, want SCORING_ENGINE_API_KEY value", got)
	}
}

func TestTriggerScoringSendsAPIKeyAndAuth(t *testing.T) {
	t.Setenv("SCORING_ENGINE_API_KEY", "svc-key")
	srv, rec := stubPython(t, http.StatusOK, map[string]interface{}{"status": "SCORED"})
	c := NewPythonClient(srv.URL)

	if _, err := c.TriggerScoring("Bearer tok"); err != nil {
		t.Fatalf("TriggerScoring: %v", err)
	}
	if rec.method != http.MethodPost || rec.path != "/api/v1/credit-reports" {
		t.Errorf("request = %s %s, want POST /api/v1/credit-reports", rec.method, rec.path)
	}
	if rec.header.Get("X-Api-Key") != "svc-key" {
		t.Errorf("X-Api-Key = %q, want svc-key", rec.header.Get("X-Api-Key"))
	}
	if rec.header.Get("Authorization") != "Bearer tok" {
		t.Errorf("Authorization = %q, want Bearer tok", rec.header.Get("Authorization"))
	}
}

func TestPythonClientErrorMapping(t *testing.T) {
	t.Run("404 becomes not found", func(t *testing.T) {
		srv, _ := stubPython(t, http.StatusNotFound, nil)
		_, err := NewPythonClient(srv.URL).GetCreditScore(404, "")
		if err == nil || err.Error() != "not found" {
			t.Fatalf("err = %v, want \"not found\"", err)
		}
	})

	t.Run("500 becomes status error", func(t *testing.T) {
		srv, _ := stubPython(t, http.StatusInternalServerError, map[string]string{"detail": "boom"})
		_, err := NewPythonClient(srv.URL).GetCreditScore(1, "")
		if err == nil {
			t.Fatal("expected error for 500 response")
		}
	})

	t.Run("invalid JSON", func(t *testing.T) {
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			_, _ = w.Write([]byte("<html>not json</html>"))
		}))
		defer srv.Close()
		_, err := NewPythonClient(srv.URL).GetCreditScore(1, "")
		if err == nil {
			t.Fatal("expected unmarshal error for HTML body")
		}
	})

	t.Run("connection refused", func(t *testing.T) {
		_, err := NewPythonClient("http://127.0.0.1:1").GetCreditScore(1, "")
		if err == nil {
			t.Fatal("expected transport error")
		}
	})
}
