package routing

import (
	"math/rand"
	"sync"

	"github.com/athena/scoring-service/internal/model"
	"github.com/rs/zerolog/log"
)

type ChampionChallengerRouter struct {
	mu             sync.RWMutex
	challengerPct  float64
}

func NewRouter(initialPct float64) *ChampionChallengerRouter {
	pct := initialPct
	if pct < 0 {
		pct = 0
	} else if pct > 1 {
		pct = 1
	}
	return &ChampionChallengerRouter{challengerPct: pct}
}

// Route returns the model target for this request.
// If challengerPct = 0.0 -> always CHAMPION.
// If challengerPct = 0.2 -> 20% of requests go to CHALLENGER.
func (r *ChampionChallengerRouter) Route() model.ModelTarget {
	r.mu.RLock()
	pct := r.challengerPct
	r.mu.RUnlock()

	if pct > 0.0 && rand.Float64() < pct {
		log.Debug().Float64("pct", pct).Msg("routing to CHALLENGER")
		return model.Challenger
	}
	return model.Champion
}

func (r *ChampionChallengerRouter) GetChallengerPct() float64 {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.challengerPct
}

func (r *ChampionChallengerRouter) UpdateChallengerPct(newPct float64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if newPct < 0 {
		newPct = 0
	} else if newPct > 1 {
		newPct = 1
	}
	r.challengerPct = newPct
	log.Info().Float64("pct", newPct*100).Msg("champion-challenger split updated")
}
