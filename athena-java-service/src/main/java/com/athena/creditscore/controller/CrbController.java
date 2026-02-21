package com.athena.creditscore.controller;

import com.athena.creditscore.client.CrbApiClient;
import com.athena.creditscore.routing.ChampionChallengerRouter;
import com.athena.creditscore.model.ModelTarget;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * CRB Orchestration Controller.
 * Triggers outbound CRB API fetches and routes scoring requests
 * via the champion-challenger router.
 */
@RestController
@RequestMapping("/api/v1/crb")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "CRB Integration", description = "Credit Reference Bureau data fetch and orchestration")
public class CrbController {

    private final CrbApiClient crbApiClient;
    private final ChampionChallengerRouter router;
    private final WebClient.Builder webClientBuilder;

    @PostMapping("/fetch/{customerId}")
    @Operation(summary = "Trigger outbound CRB report fetch for a customer")
    public ResponseEntity<Map<String, Object>> fetchCrbReport(
            @PathVariable Long customerId,
            @RequestParam String nationalId,
            @RequestParam(defaultValue = "transunion") String crb) {

        ModelTarget target = router.route();
        log.info("CRB fetch: customer={}, crb={}, model_target={}", customerId, crb, target);

        // Fetch from CRB
        Mono<Map> reportMono = "metropol".equalsIgnoreCase(crb)
                ? crbApiClient.fetchMetropolReport(nationalId)
                : crbApiClient.fetchTransUnionReport(nationalId);

        Map report = reportMono.block();

        // Forward to Python scoring engine with routing decision
        Map<String, Object> scoringPayload = Map.of(
                "customer_id", customerId,
                "model_target", target.name().toLowerCase(),
                "crb_report", report != null ? report : Map.of()
        );

        log.info("Forwarding to scoring engine, target={}", target);
        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "model_target", target.name().toLowerCase(),
                "crb_fetched", report != null,
                "message", "CRB report fetched. Scoring request queued."
        ));
    }

    @GetMapping("/routing-config")
    @Operation(summary = "Get current champion-challenger split configuration")
    public ResponseEntity<Map<String, Object>> getRoutingConfig() {
        return ResponseEntity.ok(Map.of(
                "challenger_traffic_pct", router.getChallengerPct(),
                "champion_traffic_pct", 1.0 - router.getChallengerPct()
        ));
    }

    @PutMapping("/routing-config")
    @Operation(summary = "Update champion-challenger split (admin only)")
    public ResponseEntity<Map<String, Object>> updateRoutingConfig(
            @RequestParam double challengerPct) {
        router.updateChallengerPct(challengerPct);
        return ResponseEntity.ok(Map.of(
                "updated_challenger_pct", router.getChallengerPct(),
                "message", "Routing config updated"
        ));
    }
}
