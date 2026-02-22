package com.athena.creditscore.routing;

import com.athena.creditscore.model.ModelTarget;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Random;

/**
 * Champion-Challenger traffic router.
 * Routes a configurable percentage of scoring requests to the challenger model.
 * Routing decision is logged to champion_challenger_log via CreditQueryService.
 */
@Component
@Slf4j
public class ChampionChallengerRouter {

    @Value("${challenger.traffic.pct:0.0}")
    private double challengerPct;

    private final Random random = new Random();

    /**
     * Return the model target for this request.
     * If challengerPct = 0.0 → always CHAMPION.
     * If challengerPct = 0.2 → 20% of requests go to CHALLENGER.
     */
    public ModelTarget route() {
        if (challengerPct > 0.0 && random.nextDouble() < challengerPct) {
            log.debug("Routing to CHALLENGER (configured pct: {})", challengerPct);
            return ModelTarget.CHALLENGER;
        }
        return ModelTarget.CHAMPION;
    }

    public double getChallengerPct() {
        return challengerPct;
    }

    public void updateChallengerPct(double newPct) {
        this.challengerPct = Math.max(0.0, Math.min(1.0, newPct));
        log.info("Champion-challenger split updated to {}%", this.challengerPct * 100);
    }
}
