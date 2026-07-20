package routing

import (
	"math"
	"sync"
	"testing"

	"github.com/athena/scoring-service/internal/model"
)

func TestRouteZeroPctIsAlwaysChampion(t *testing.T) {
	r := NewRouter(0.0)
	for i := 0; i < 5000; i++ {
		if got := r.Route(); got != model.Champion {
			t.Fatalf("iteration %d: Route() = %q, want champion with pct=0", i, got)
		}
	}
}

func TestRouteFullPctIsAlwaysChallenger(t *testing.T) {
	r := NewRouter(1.0)
	for i := 0; i < 5000; i++ {
		if got := r.Route(); got != model.Challenger {
			t.Fatalf("iteration %d: Route() = %q, want challenger with pct=1", i, got)
		}
	}
}

func TestRouteSplitProportion(t *testing.T) {
	const pct = 0.2
	const n = 50000
	r := NewRouter(pct)

	challenger := 0
	for i := 0; i < n; i++ {
		if r.Route() == model.Challenger {
			challenger++
		}
	}
	got := float64(challenger) / n
	// 3-sigma tolerance for a binomial(n, 0.2): sigma ≈ 0.0018
	if math.Abs(got-pct) > 0.01 {
		t.Fatalf("challenger share = %.4f, want %.2f ± 0.01", got, pct)
	}
}

func TestNewRouterClampsPct(t *testing.T) {
	cases := []struct {
		in   float64
		want float64
	}{
		{-0.5, 0.0},
		{0.0, 0.0},
		{0.35, 0.35},
		{1.0, 1.0},
		{7.0, 1.0},
	}
	for _, tc := range cases {
		if got := NewRouter(tc.in).GetChallengerPct(); got != tc.want {
			t.Errorf("NewRouter(%v) pct = %v, want %v", tc.in, got, tc.want)
		}
	}
}

func TestUpdateChallengerPctClampsAndApplies(t *testing.T) {
	r := NewRouter(0.0)

	r.UpdateChallengerPct(0.4)
	if got := r.GetChallengerPct(); got != 0.4 {
		t.Fatalf("pct after update = %v, want 0.4", got)
	}

	r.UpdateChallengerPct(-3)
	if got := r.GetChallengerPct(); got != 0 {
		t.Fatalf("pct after negative update = %v, want 0", got)
	}

	r.UpdateChallengerPct(42)
	if got := r.GetChallengerPct(); got != 1 {
		t.Fatalf("pct after >1 update = %v, want 1", got)
	}

	// Back to 0: routing must become deterministic champion again.
	r.UpdateChallengerPct(0)
	for i := 0; i < 1000; i++ {
		if r.Route() != model.Champion {
			t.Fatal("Route() returned challenger after pct reset to 0")
		}
	}
}

// TestConcurrentRouteAndUpdate exercises the RWMutex paths; run with -race.
func TestConcurrentRouteAndUpdate(t *testing.T) {
	r := NewRouter(0.5)
	var wg sync.WaitGroup
	for w := 0; w < 8; w++ {
		wg.Add(1)
		go func(seed int) {
			defer wg.Done()
			for i := 0; i < 2000; i++ {
				switch i % 4 {
				case 0:
					r.UpdateChallengerPct(float64(seed) / 8)
				case 1:
					_ = r.GetChallengerPct()
				default:
					_ = r.Route()
				}
			}
		}(w)
	}
	wg.Wait()
}
