package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * Customer Profile Controller.
 *
 * Adapted from athena-device-finance customer-service patterns.
 * Provides self-service profile management for customers and
 * admin-facing CRUD for analysts/admins.
 */
@RestController
@RequestMapping("/api/v1/customers")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Customer Profile", description = "Profile management, disputes and consent")
public class CustomerProfileController {

        private final RabbitTemplate rabbitTemplate;
        private final org.springframework.jdbc.core.JdbcTemplate jdbcTemplate;

        @org.springframework.beans.factory.annotation.Value("${scoring.engine.url:http://athena-python-service:8001}")
        private String scoringEngineUrl;

        // ── GET search customers ──────────────────────────────────────────────────

        @GetMapping("/search")
        @Operation(summary = "Search customers by ID, name, or phone")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER')")
        public ResponseEntity<java.util.List<Map<String, Object>>> searchCustomers(
                        @RequestParam(name = "q", defaultValue = "") String query) {
                String likeQuery = "%" + query + "%";
                Long idQuery = null;
                try {
                        idQuery = Long.parseLong(query);
                } catch (Exception e) {
                }

                String sql = "SELECT c.customer_id as id, c.first_name || ' ' || c.last_name as name, " +
                                "c.mobile_number as phone, 'General' as sector, " +
                                "COALESCE(cse.final_score, 0) as score, " +
                                "COALESCE(cse.pd_probability, 0.0) as pd " +
                                "FROM customers c " +
                                "LEFT JOIN (SELECT DISTINCT ON (customer_id) customer_id, final_score, pd_probability "
                                +
                                "           FROM credit_score_events ORDER BY customer_id, scored_at DESC) cse " +
                                "ON c.customer_id = cse.customer_id " +
                                "WHERE ? = '' OR c.first_name ILIKE ? OR c.last_name ILIKE ? OR c.mobile_number ILIKE ? "
                                +
                                "OR c.customer_id = ? " +
                                "ORDER BY c.customer_id ASC " +
                                "LIMIT 50";

                var results = jdbcTemplate.queryForList(sql, query, likeQuery, likeQuery, likeQuery,
                                idQuery != null ? idQuery : -1L);
                return ResponseEntity.ok(results);
        }

        // ── GET profile ───────────────────────────────────────────────────────────

        @GetMapping("/{customerId}")
        @Operation(summary = "Get customer profile")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CUSTOMER')")
        public ResponseEntity<Map<String, Object>> getProfile(@PathVariable Long customerId) {
                try {
                        String sql = "SELECT c.customer_id AS id, " +
                                        "c.first_name || ' ' || c.last_name AS name, " +
                                        "c.first_name, c.last_name, c.mobile_number AS phone, " +
                                        "c.email, c.national_id, c.date_of_birth, c.gender, " +
                                        "c.county, c.region, c.bank_name, c.account_number, " +
                                        "c.verification_status, c.crb_consent, c.registration_channel, c.created_at, " +
                                        "COALESCE(cse.final_score, 0) AS score, " +
                                        "COALESCE(cse.score_band, 'N/A') AS score_band, " +
                                        "COALESCE(cse.pd_probability, 0.0) AS pd_probability, " +
                                        "cse.scored_at " +
                                        "FROM customers c " +
                                        "LEFT JOIN ( " +
                                        "    SELECT DISTINCT ON (customer_id) " +
                                        "           customer_id, final_score, score_band, pd_probability, scored_at " +
                                        "    FROM credit_score_events ORDER BY customer_id, scored_at DESC " +
                                        ") cse ON c.customer_id = cse.customer_id " +
                                        "WHERE c.customer_id = ?";
                        Map<String, Object> profile = jdbcTemplate.queryForMap(sql, customerId);
                        return ResponseEntity.ok(profile);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                        return ResponseEntity.status(404).body(Map.of(
                                        "error", "Customer not found",
                                        "customer_id", customerId));
                }
        }

        // ── PUT update profile ────────────────────────────────────────────────────

        @PutMapping("/{customerId}")
        @Operation(summary = "Update customer profile information")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST') or #customerId.toString() == authentication.name")
        public ResponseEntity<Map<String, Object>> updateProfile(
                        @PathVariable Long customerId,
                        @RequestBody Map<String, Object> updates,
                        Authentication auth) {
                log.info("Profile update: customer={}, by={}", customerId, auth.getName());
                // Emit audit event
                _publishEvent("PROFILE_UPDATED", customerId, updates, auth.getName());
                return ResponseEntity.ok(Map.of(
                                "customer_id", customerId,
                                "updated_fields", updates.keySet(),
                                "updated_at", LocalDateTime.now().toString()));
        }

        // ── POST file dispute ─────────────────────────────────────────────────────

        @PostMapping("/{customerId}/disputes")
        @Operation(summary = "File a credit report dispute")
        @PreAuthorize("hasAnyRole('ADMIN') or #customerId.toString() == authentication.name")
        public ResponseEntity<Map<String, Object>> fileDispute(
                        @PathVariable Long customerId,
                        @RequestBody Map<String, String> disputeBody,
                        Authentication auth) {
                String disputeId = "DSP-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
                String description = disputeBody.getOrDefault("description", "");
                String field = disputeBody.getOrDefault("disputed_field", "");

                log.info("Dispute filed: customer={}, id={}, field={}", customerId, disputeId, field);

                // Persist to DB
                jdbcTemplate.update(
                                "INSERT INTO disputes (customer_id, reason, status) VALUES (?, ?, 'OPEN')",
                                customerId, description.isEmpty() ? field : description);

                // Publish to notification queue — will trigger email to compliance team
                rabbitTemplate.convertAndSend(
                                "athena.exchange",
                                "athena.notification.routingKey",
                                Map.of(
                                                "type", "DISPUTE_FILED",
                                                "disputeId", disputeId,
                                                "customerId", customerId,
                                                "field", field,
                                                "description", description,
                                                "filedAt", LocalDateTime.now().toString()));

                return ResponseEntity.ok(Map.of(
                                "dispute_id", disputeId,
                                "customer_id", customerId,
                                "status", "OPEN",
                                "disputed_field", field,
                                "filed_at", LocalDateTime.now().toString(),
                                "message", "Dispute filed. Our team will review within 5 business days."));
        }

        // ── GET disputes ──────────────────────────────────────────────────────────

        @GetMapping("/{customerId}/disputes")
        @Operation(summary = "List all disputes for a customer")
        @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CUSTOMER')")
        public ResponseEntity<java.util.List<Map<String, Object>>> getDisputes(@PathVariable Long customerId) {
                var disputes = jdbcTemplate.queryForList(
                                "SELECT dispute_id as id, reason as field, reason as desc, status, " +
                                                "CAST(created_at AS DATE) as filed " +
                                                "FROM disputes WHERE customer_id = ? ORDER BY created_at DESC",
                                customerId);
                return ResponseEntity.ok(disputes);
        }

        // ── GET consents ──────────────────────────────────────────────────────────

        @GetMapping("/{customerId}/consents")
        @Operation(summary = "List active consents for a customer")
        @PreAuthorize("hasAnyRole('ADMIN','CUSTOMER')")
        public ResponseEntity<java.util.List<Map<String, Object>>> getConsents(@PathVariable Long customerId) {
                var consents = jdbcTemplate.queryForList(
                                "SELECT consent_id as id, CAST(partner_id AS VARCHAR) as name, " +
                                                "scope, CAST(created_at AS DATE) as granted " +
                                                "FROM consents WHERE customer_id = ? AND revoked = false " +
                                                "ORDER BY created_at DESC",
                                customerId);
                return ResponseEntity.ok(consents);
        }

        // ── DELETE revoke consent ─────────────────────────────────────────────────

        @DeleteMapping("/{customerId}/consents/{consentId}")
        @Operation(summary = "Revoke a specific consent by consent_id")
        @PreAuthorize("hasAnyRole('ADMIN','CUSTOMER')")
        public ResponseEntity<Map<String, Object>> revokeConsent(
                        @PathVariable Long customerId,
                        @PathVariable Long consentId) {
                int updated = jdbcTemplate.update(
                                "UPDATE consents SET revoked = true WHERE customer_id = ? AND consent_id = ?",
                                customerId, consentId);
                log.info("Consent revoked: customer={}, consentId={}, rows={}", customerId, consentId, updated);
                return ResponseEntity.ok(Map.of(
                                "customer_id", customerId,
                                "consent_id", consentId,
                                "revoked", updated > 0));
        }

        // ── PUT grant consent ─────────────────────────────────────────────────────

        @PutMapping("/{customerId}/consent")
        @Operation(summary = "Customer grants data access consent to a partner")
        @PreAuthorize("#customerId.toString() == authentication.name or hasRole('ADMIN')")
        public ResponseEntity<Map<String, Object>> grantConsent(
                        @PathVariable Long customerId,
                        @RequestBody Map<String, String> body,
                        Authentication auth) {
                String partnerId = body.getOrDefault("partner_id", "unknown");
                String scope = body.getOrDefault("scope", "CREDIT_SCORE");
                String consentToken = UUID.randomUUID().toString();

                log.info("Consent granted: customer={}, partner={}, scope={}", customerId, partnerId, scope);

                // Persist consent to DB
                long partnerIdLong = Math.abs((long) partnerId.hashCode());
                jdbcTemplate.update(
                                "INSERT INTO consents (customer_id, partner_id, scope, token_jti, expires_at) " +
                                                "VALUES (?, ?, ?, ?, NOW() + INTERVAL '1 year') " +
                                                "ON CONFLICT (token_jti) DO NOTHING",
                                customerId, partnerIdLong, scope, consentToken);

                _publishEvent("CONSENT_GRANTED", customerId, Map.of("partner_id", partnerId, "scope", scope),
                                auth.getName());

                return ResponseEntity.ok(Map.of(
                                "consent_token", consentToken,
                                "customer_id", customerId,
                                "partner_id", partnerId,
                                "scope", scope,
                                "expires_at", LocalDateTime.now().plusYears(1).toString()));
        }

        // ── Helper ────────────────────────────────────────────────────────────────

        private void _publishEvent(String type, Long customerId, Object payload, String actor) {
                try {
                        rabbitTemplate.convertAndSend(
                                        "athena.exchange",
                                        "athena.scoring.routingKey",
                                        Map.of("type", type, "customerId", customerId, "payload", payload, "actor",
                                                        actor, "ts", LocalDateTime.now().toString()));
                } catch (Exception e) {
                        log.error("Event publish failed: {}", e.getMessage());
                }
        }
}
