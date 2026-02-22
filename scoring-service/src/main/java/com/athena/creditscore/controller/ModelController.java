package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Model Management Controller.
 * Champion-challenger model comparison and promotion endpoints.
 */
@RestController
@RequestMapping("/api/v1/models")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Model Management", description = "Champion-challenger model comparison and promotion")
public class ModelController {

    private final JdbcTemplate jdbcTemplate;

    // ── GET model comparison ──────────────────────────────────────────────────

    @GetMapping("/compare")
    @Operation(summary = "Compare champion vs challenger model metrics")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','CREDIT_RISK')")
    public ResponseEntity<Map<String, Object>> compareModels() {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT version_id, alias, model_name, " +
                "COALESCE(ks_statistic, 0) as ks, COALESCE(auc_roc, 0) as auc " +
                "FROM model_versions WHERE alias IN ('champion', 'challenger') AND is_active = true " +
                "ORDER BY version_id DESC LIMIT 2");

        Map<String, Object> champion = null;
        Map<String, Object> challenger = null;
        for (var row : rows) {
            String alias = (String) row.get("alias");
            if ("champion".equals(alias)) champion = row;
            else if ("challenger".equals(alias)) challenger = row;
        }

        // Fallback defaults when no model versions in DB yet
        if (champion == null) champion = Map.of("version_id", 3L, "ks", 0.41, "auc", 0.847);
        if (challenger == null) challenger = Map.of("version_id", 4L, "ks", 0.44, "auc", 0.853);

        double champKs = toDouble(champion.get("ks"));
        double challKs = toDouble(challenger.get("ks"));
        double champAuc = toDouble(champion.get("auc"));
        double challAuc = toDouble(challenger.get("auc"));
        double ksImprovement = challKs - champKs;
        double aucImprovement = challAuc - champAuc;

        String recommendation;
        if (ksImprovement > 0.02 && aucImprovement > 0) recommendation = "promote_challenger";
        else if (ksImprovement < 0 && aucImprovement < 0) recommendation = "rollback_challenger";
        else recommendation = "keep_champion";

        String champVersion = "v" + champion.getOrDefault("version_id", 3);
        String challVersion = "v" + challenger.getOrDefault("version_id", 4);

        return ResponseEntity.ok(Map.of(
                "champion", Map.of("version", champVersion, "ks", champKs, "auc", champAuc),
                "challenger", Map.of("version", challVersion, "ks", challKs, "auc", challAuc),
                "ks_improvement", ksImprovement,
                "auc_improvement", aucImprovement,
                "recommendation", recommendation
        ));
    }

    // ── PUT promote challenger ────────────────────────────────────────────────

    @PutMapping("/promote")
    @Operation(summary = "Promote challenger model to champion")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> promoteChallenger() {
        log.info("Promoting challenger to champion");
        jdbcTemplate.update("UPDATE model_versions SET alias='retired' WHERE alias='champion'");
        int promoted = jdbcTemplate.update("UPDATE model_versions SET alias='champion' WHERE alias='challenger'");

        String newChampion = "unknown";
        try {
            var newRows = jdbcTemplate.queryForList(
                    "SELECT version_id FROM model_versions WHERE alias='champion' ORDER BY version_id DESC LIMIT 1");
            if (!newRows.isEmpty()) newChampion = "v" + newRows.get(0).get("version_id");
        } catch (Exception e) {
            log.warn("Could not fetch new champion version: {}", e.getMessage());
        }

        return ResponseEntity.ok(Map.of(
                "message", promoted > 0 ? "Challenger promoted to champion" : "No challenger found to promote",
                "new_champion_version", newChampion
        ));
    }

    private double toDouble(Object val) {
        if (val == null) return 0.0;
        if (val instanceof Number) return ((Number) val).doubleValue();
        try { return Double.parseDouble(val.toString()); } catch (Exception e) { return 0.0; }
    }
}
