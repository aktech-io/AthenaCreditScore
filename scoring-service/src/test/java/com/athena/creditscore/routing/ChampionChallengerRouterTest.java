package com.athena.creditscore.routing;

import com.athena.creditscore.model.ModelTarget;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.stream.IntStream;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

@DisplayName("ChampionChallengerRouter Tests")
class ChampionChallengerRouterTest {

    private ChampionChallengerRouter router;

    @BeforeEach
    void setUp() {
        router = new ChampionChallengerRouter();
    }

    @Test
    @DisplayName("0% challenger → always returns CHAMPION")
    void shouldAlwaysReturnChampionWhenChallengerPctZero() {
        ReflectionTestUtils.setField(router, "challengerPct", 0.0);
        IntStream.range(0, 100).forEach(i ->
                assertThat(router.route()).isEqualTo(ModelTarget.CHAMPION)
        );
    }

    @Test
    @DisplayName("100% challenger → always returns CHALLENGER")
    void shouldAlwaysReturnChallengerWhenChallengerPctOne() {
        ReflectionTestUtils.setField(router, "challengerPct", 1.0);
        IntStream.range(0, 100).forEach(i ->
                assertThat(router.route()).isEqualTo(ModelTarget.CHALLENGER)
        );
    }

    @Test
    @DisplayName("50% split → approximately 40-60% challenger in 1000 requests")
    void shouldSplitApproximatelyHalfAndHalf() {
        ReflectionTestUtils.setField(router, "challengerPct", 0.5);
        AtomicInteger challengerCount = new AtomicInteger(0);
        int total = 1000;

        IntStream.range(0, total).forEach(i -> {
            if (router.route() == ModelTarget.CHALLENGER) challengerCount.incrementAndGet();
        });

        double pct = (double) challengerCount.get() / total;
        // With 1000 samples, expect within 40-60% for 50% split (generous bounds)
        assertThat(pct).isBetween(0.40, 0.60);
    }

    @Test
    @DisplayName("updateChallengerPct should change the routing split")
    void shouldUpdatePctAtRuntime() {
        router.updateChallengerPct(0.0);
        assertThat(router.getChallengerPct()).isEqualTo(0.0);

        router.updateChallengerPct(0.3);
        assertThat(router.getChallengerPct()).isEqualTo(0.3);
    }

    @Test
    @DisplayName("updateChallengerPct should clamp above 1.0 to 1.0")
    void shouldClampAboveOne() {
        router.updateChallengerPct(1.5);
        assertThat(router.getChallengerPct()).isEqualTo(1.0);
    }

    @Test
    @DisplayName("updateChallengerPct should clamp below 0.0 to 0.0")
    void shouldClampBelowZero() {
        router.updateChallengerPct(-0.5);
        assertThat(router.getChallengerPct()).isEqualTo(0.0);
    }

    @Test
    @DisplayName("route() returns one of the two valid model targets")
    void shouldReturnValidModelTarget() {
        ReflectionTestUtils.setField(router, "challengerPct", 0.5);
        ModelTarget target = router.route();
        assertThat(target).isIn(ModelTarget.CHAMPION, ModelTarget.CHALLENGER);
    }
}
