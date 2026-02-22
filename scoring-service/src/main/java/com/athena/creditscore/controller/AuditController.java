package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Audit Log Controller.
 * Exposes tamper-evident partner data access log for compliance review.
 */
@RestController
@RequestMapping("/api/v1/audit")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Audit Log", description = "Partner data access audit log (compliance)")
public class AuditController {

    private final JdbcTemplate jdbcTemplate;

    @GetMapping
    @Operation(summary = "Get audit log entries (paginated, filterable by action/outcome)")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','CREDIT_RISK')")
    public ResponseEntity<List<Map<String, Object>>> getAuditLog(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size,
            @RequestParam(required = false) String action,
            @RequestParam(required = false) String outcome) {

        int offset = page * size;
        StringBuilder sql = new StringBuilder(
                "SELECT log_id as id, " +
                "TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as ts, " +
                "COALESCE(actor_id, 'SYSTEM') as partner, " +
                "COALESCE(CAST((payload->>'customerId') AS VARCHAR), " +
                "         CAST((payload->>'customer_id') AS VARCHAR), '') as customer, " +
                "COALESCE(action, '') as action, " +
                "COALESCE(resource, 'OK') as outcome, " +
                "COALESCE(CAST(ip_address AS VARCHAR), '') as ip " +
                "FROM audit_log WHERE 1=1");

        List<Object> params = new ArrayList<>();
        if (action != null && !action.isBlank()) {
            sql.append(" AND action = ?");
            params.add(action);
        }
        if (outcome != null && !outcome.isBlank()) {
            sql.append(" AND resource = ?");
            params.add(outcome);
        }
        sql.append(" ORDER BY created_at DESC LIMIT ? OFFSET ?");
        params.add(size);
        params.add(offset);

        List<Map<String, Object>> results = jdbcTemplate.queryForList(sql.toString(), params.toArray());
        return ResponseEntity.ok(results);
    }
}
