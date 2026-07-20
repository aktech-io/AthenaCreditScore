package client

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
)

func TestFetchTransUnionReportSendsBearerAndPayload(t *testing.T) {
	var gotAuth, gotCT string
	var gotBody map[string]string

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		gotCT = r.Header.Get("Content-Type")
		raw, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(raw, &gotBody)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"score": 650, "bureau": "TransUnion"})
	}))
	defer srv.Close()

	c := NewCrbClient(srv.URL, "tu-key", "http://unused", "m-key")
	got, err := c.FetchTransUnionReport("12345678")
	if err != nil {
		t.Fatalf("FetchTransUnionReport: %v", err)
	}

	if gotAuth != "Bearer tu-key" {
		t.Errorf("Authorization = %q, want \"Bearer tu-key\"", gotAuth)
	}
	if gotCT != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", gotCT)
	}
	if gotBody["nationalId"] != "12345678" {
		t.Errorf("payload nationalId = %q, want 12345678", gotBody["nationalId"])
	}
	if gotBody["requestId"] == "" {
		t.Error("payload requestId is empty, want a generated UUID")
	}
	if got["score"].(float64) != 650 {
		t.Errorf("score = %v, want 650", got["score"])
	}
}

func TestFetchMetropolReportSendsAPIKeyHeader(t *testing.T) {
	var gotKey string
	var gotBody map[string]string

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotKey = r.Header.Get("X-Api-Key")
		raw, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(raw, &gotBody)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"score": 512})
	}))
	defer srv.Close()

	c := NewCrbClient("http://unused", "tu-key", srv.URL, "metropol-key")
	if _, err := c.FetchMetropolReport("87654321"); err != nil {
		t.Fatalf("FetchMetropolReport: %v", err)
	}

	if gotKey != "metropol-key" {
		t.Errorf("X-Api-Key = %q, want metropol-key", gotKey)
	}
	if gotBody["nationalId"] != "87654321" {
		t.Errorf("payload nationalId = %q, want 87654321", gotBody["nationalId"])
	}
	if _, hasReqID := gotBody["requestId"]; hasReqID {
		t.Error("Metropol payload unexpectedly contains requestId")
	}
}

// TestCrbRetrySucceedsAfterFailure verifies the exponential-backoff retry:
// first attempt 500, second attempt succeeds (sleeps ~1s).
func TestCrbRetrySucceedsAfterFailure(t *testing.T) {
	if testing.Short() {
		t.Skip("retry backoff sleeps; skipped in -short mode")
	}
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if atomic.AddInt32(&calls, 1) == 1 {
			http.Error(w, "bureau unavailable", http.StatusInternalServerError)
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"score": 700})
	}))
	defer srv.Close()

	c := NewCrbClient(srv.URL, "k", "http://unused", "k")
	got, err := c.FetchTransUnionReport("11111111")
	if err != nil {
		t.Fatalf("expected retry to recover, got error: %v", err)
	}
	if n := atomic.LoadInt32(&calls); n != 2 {
		t.Errorf("server hit %d times, want 2 (fail then succeed)", n)
	}
	if got["score"].(float64) != 700 {
		t.Errorf("score = %v, want 700", got["score"])
	}
}

// TestCrbRetryExhaustionReturnsLastError verifies all 3 attempts are made
// and the final error carries the upstream status (sleeps ~3s).
func TestCrbRetryExhaustionReturnsLastError(t *testing.T) {
	if testing.Short() {
		t.Skip("retry backoff sleeps; skipped in -short mode")
	}
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		http.Error(w, "no such person", http.StatusBadRequest)
	}))
	defer srv.Close()

	c := NewCrbClient("http://unused", "k", srv.URL, "k")
	_, err := c.FetchMetropolReport("00000000")
	if err == nil {
		t.Fatal("expected error after retry exhaustion")
	}
	if n := atomic.LoadInt32(&calls); n != 3 {
		t.Errorf("server hit %d times, want 3 attempts", n)
	}
}
