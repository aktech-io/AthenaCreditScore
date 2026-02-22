package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/disputes")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Disputes", description = "Admin view of all disputes")
public class DisputeController {

    private final JdbcTemplate jdbcTemplate;

    @GetMapping
    @Operation(summary = "List all disputes across all customers")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CREDIT_RISK')")
    public ResponseEntity<List<Map<String, Object>>> listDisputes(
            @RequestParam(name = "status", required = false) String status) {
        String sql = "SELECT d.dispute_id as id, d.customer_id as \"customerId\", " +
                "c.first_name || ' ' || c.last_name as customer, " +
                "'Credit Report' as field, d.reason as desc, " +
                "d.status, CAST(d.created_at AS DATE) as filed " +
                "FROM disputes d " +
                "JOIN customers c ON d.customer_id = c.customer_id ";

        List<Map<String, Object>> results;
        if (status != null && !status.isEmpty() && !status.equals("ALL")) {
            sql += "WHERE d.status = ? ORDER BY d.created_at DESC";
            results = jdbcTemplate.queryForList(sql, status);
        } else {
            sql += "ORDER BY d.created_at DESC";
            results = jdbcTemplate.queryForList(sql);
        }

        return ResponseEntity.ok(results);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update dispute status")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST')")
    public ResponseEntity<Void> updateDispute(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        String status = body.get("status");
        if (status != null) {
            jdbcTemplate.update("UPDATE disputes SET status = ? WHERE dispute_id = ?", status, id);
        }
        return ResponseEntity.ok().build();
    }
}
