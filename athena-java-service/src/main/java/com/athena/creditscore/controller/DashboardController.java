package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/v1/dashboard")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Admin Dashboard", description = "Aggregate statistics for the admin dashboard")
public class DashboardController {

    private final JdbcTemplate jdbcTemplate;

    @GetMapping("/stats")
    @Operation(summary = "Get aggregate statistics for the dashboard")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CREDIT_RISK')")
    public ResponseEntity<Map<String, Object>> getDashboardStats() {
        Map<String, Object> stats = new HashMap<>();

        // Total Scored
        Integer totalScored = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM credit_score_events", Integer.class);
        stats.put("totalScored", totalScored != null ? totalScored : 0);

        // Avg Score
        Double avgScore = jdbcTemplate.queryForObject("SELECT AVG(final_score) FROM credit_score_events", Double.class);
        stats.put("avgScore", avgScore != null ? Math.round(avgScore) : 0);

        // Approval Rate (Score >= 500)
        Double approvalRate = jdbcTemplate.queryForObject(
            "SELECT (COUNT(*) FILTER (WHERE final_score >= 500)::float / NULLIF(COUNT(*), 0)) FROM credit_score_events", 
            Double.class);
        stats.put("approvalRate", approvalRate != null ? approvalRate : 0.0);

        // Default Rate
        Double defaultRate = jdbcTemplate.queryForObject(
            "SELECT (COUNT(*) FILTER (WHERE status = 'DEFAULTED')::float / NULLIF(COUNT(*), 0)) FROM loans", 
            Double.class);
        stats.put("defaultRate", defaultRate != null ? defaultRate : 0.0);

        // Open Disputes
        Integer openDisputes = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM disputes WHERE status IN ('OPEN', 'UNDER_REVIEW')", 
            Integer.class);
        stats.put("openDisputes", openDisputes != null ? openDisputes : 0);
        
        // Mocked or external values until MLflow integration is deeper
        stats.put("ksStatistic", 0.42);
        stats.put("psiValue", 0.08);
        stats.put("championVersion", "v1.2");
        stats.put("challengerVersion", "v1.3-xgb");
        stats.put("challengerPct", 0.20);
        
        return ResponseEntity.ok(stats);
    }
}
