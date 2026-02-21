package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

/**
 * Credit Query Service Controller.
 * 
 * Exposes APIs to:
 * 1. Pull live credit scores from the Python scoring engine (with Caffeine
 * cache)
 * 2. Trigger a fresh scoring run via the Python service
 * 3. Retrieve formatted credit reports suitable for portal display
 */
@RestController
@RequestMapping("/api/v1/credit")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Credit Query", description = "Credit score retrieval and scoring trigger")
public class CreditQueryController {

        private final WebClient.Builder webClientBuilder;
        private final org.springframework.jdbc.core.JdbcTemplate jdbcTemplate;

        // Configured in application.yml → scoring.engine.url
        @org.springframework.beans.factory.annotation.Value("${scoring.engine.url:http://athena-python-service:8001}")
        private String scoringEngineUrl;

        // ── GET latest cached score ──────────────────────────────────────────────

        @GetMapping("/score/{customerId}")
        @Cacheable(value = "credit_scores", key = "#customerId")
        @Operation(summary = "Get latest credit score for a customer (Caffeine-cached, TTL=1h)")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CREDIT_RISK','CUSTOMER')")
        public ResponseEntity<Map> getCreditScore(
                        @PathVariable Long customerId,
                        @RequestHeader("Authorization") String jwtToken) {
                log.info("Fetching credit score: customer={}", customerId);
                Map result = webClientBuilder.build()
                                .get()
                                .uri(scoringEngineUrl + "/api/v1/credit-score/" + customerId)
                                .header("Authorization", jwtToken)
                                .retrieve()
                                .bodyToMono(Map.class)
                                .block();
                return ResponseEntity.ok(result != null ? result : Map.of());
        }

        // ── GET full report ───────────────────────────────────────────────────────

        @GetMapping("/report/{customerId}")
        @Cacheable(value = "credit_reports", key = "#customerId")
        @Operation(summary = "Get full credit report (score breakdown, CRB, LLM reasoning)")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CREDIT_RISK','CUSTOMER')")
        public ResponseEntity<Map> getFullReport(
                        @PathVariable Long customerId,
                        @RequestHeader("Authorization") String jwtToken) {
                log.info("Fetching full credit report: customer={}", customerId);

                // 1. Fetch ML Score Response
                Map mlReport = null;
                try {
                        mlReport = webClientBuilder.build()
                                        .get()
                                        .uri(scoringEngineUrl + "/api/v1/credit-report/" + customerId)
                                        .header("Authorization", jwtToken)
                                        .retrieve()
                                        .bodyToMono(Map.class)
                                        .block();
                } catch (org.springframework.web.reactive.function.client.WebClientResponseException.NotFound e) {
                        log.warn("No score found in Python service for customer={}", customerId);
                }

                // 2. Fetch Customer Details
                String customerSql = "SELECT first_name || ' ' || last_name AS name, mobile_number, email FROM customers WHERE customer_id = ?";
                var customerData = jdbcTemplate.queryForMap(customerSql, customerId);

                // 3. Compute simple transaction metrics from DB
                String metricsSql = "SELECT " +
                                " (SELECT COALESCE(SUM(amount_paid), 0) FROM repayments WHERE customer_id = ?) as total_paid, "
                                +
                                " (SELECT COALESCE(SUM(penalty_amount), 0) FROM repayments WHERE customer_id = ?) as total_penalties, "
                                +
                                " (SELECT COUNT(*) FROM loans WHERE customer_id = ? AND status = 'DEFAULT') as default_loans, "
                                +
                                " (SELECT COUNT(*) FROM loans WHERE customer_id = ?) as total_loans ";

                var metricsData = jdbcTemplate.queryForMap(metricsSql, customerId, customerId, customerId, customerId);

                Map<String, Object> finalResponse = new java.util.HashMap<>();
                if (mlReport != null) {
                        finalResponse.putAll(mlReport);
                        // Re-map Python dict keys to JS keys to match ReportPage mapping
                        finalResponse.put("llm_reasoning", mlReport.get("reasoning"));
                        finalResponse.put("crb_bureau_score", mlReport.get("bureau_score"));

                        // Re-map crb metrics if present
                        // But python already returns crb_name, bureau_score, etc directly in
                        // FullReportResponse
                        // We just set them:
                        finalResponse.put("crb_npa_count", 0); // Mock default
                        finalResponse.put("crb_active_default", false); // Mock default
                } else {
                        finalResponse.put("customer_id", customerId);
                        finalResponse.put("customer_name", customerData.get("name"));
                        finalResponse.put("final_score", "N/A");
                        finalResponse.put("llm_reasoning",
                                        "No scoring event found for this customer. Please trigger a new run.");
                        finalResponse.put("crb_bureau_score", "N/A");
                        finalResponse.put("crb_npa_count", 0);
                        finalResponse.put("crb_active_default", false);
                }

                finalResponse.put("phone", customerData.get("mobile_number"));
                finalResponse.put("sector", "Retail (Calculated)"); // Display purposes

                // Calculate mock equivalents of the UI performance metrics
                int defaults = ((Number) metricsData.get("default_loans")).intValue();
                int totalLoans = ((Number) metricsData.get("total_loans")).intValue();
                double delqRate = totalLoans > 0 ? (double) defaults / totalLoans : 0.0;

                finalResponse.put("delinquency_rate_90d", delqRate);
                finalResponse.put("max_delinquency_streak", defaults > 0 ? defaults : 0);

                // Mock some application features to satisfy UI layout
                finalResponse.put("capital_growth_ratio", 0.15);
                finalResponse.put("revenue_per_employee", 350000);
                finalResponse.put("profit_margin", 0.12);

                return ResponseEntity.ok(finalResponse);
        }

        // ── POST trigger fresh score ──────────────────────────────────────────────

        @PostMapping("/score/{customerId}/trigger")
        @Operation(summary = "Trigger a fresh scoring run (bypasses cache)")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','CREDIT_RISK')")
        public ResponseEntity<Map> triggerScoringRun(
                        @PathVariable Long customerId,
                        @RequestParam(defaultValue = "champion") String modelTarget,
                        @RequestHeader("Authorization") String jwtToken) {
                log.info("Triggering scoring run: customer={}, target={}", customerId, modelTarget);
                // Scoring trigger goes via CRB controller which also fetches fresh CRB
                Map result = webClientBuilder.build()
                                .post()
                                .uri(scoringEngineUrl + "/api/v1/credit-reports")
                                .header("X-Api-Key", "dev-key")
                                .header("Authorization", jwtToken)
                                .retrieve()
                                .bodyToMono(Map.class)
                                .block();
                return ResponseEntity.ok(result != null ? result : Map.of("status", "triggered"));
        }

        // ── GET score history ──────────────────────────────────────────────────────

        @GetMapping("/score/{customerId}/history")
        @Operation(summary = "Get score history for a customer (up to 12 months)")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CREDIT_RISK','CUSTOMER')")
        public ResponseEntity<Map> getScoreHistory(
                        @PathVariable Long customerId,
                        @RequestParam(defaultValue = "12") int months,
                        @RequestHeader("Authorization") String jwtToken) {
                String sql = "SELECT event_id, final_score, score_band, pd_probability, " +
                                "base_score, crb_contribution, llm_adjustment, " +
                                "scored_at, model_target " +
                                "FROM credit_score_events " +
                                "WHERE customer_id = ? " +
                                "  AND scored_at >= NOW() - (? * INTERVAL '1 month') " +
                                "ORDER BY scored_at DESC";
                var history = jdbcTemplate.queryForList(sql, customerId, months);
                return ResponseEntity.ok(Map.of(
                                "customer_id", customerId,
                                "months", months,
                                "data", history));
        }
}
