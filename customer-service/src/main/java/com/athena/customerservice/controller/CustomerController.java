package com.athena.customerservice.controller;

import com.athena.customerservice.client.MediaClient;
import com.athena.customerservice.dto.CustomerRequest;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/customers")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Customer", description = "Customer profile, disputes and consent")
public class CustomerController {

    private final JdbcTemplate jdbcTemplate;
    private final RabbitTemplate rabbitTemplate;
    private final MediaClient mediaClient;

    // ──────────────────────────────────────────────────────────────
    // LIST / SEARCH
    // ──────────────────────────────────────────────────────────────

    @GetMapping
    @Operation(summary = "Get all customers (paginated)")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER')")
    public ResponseEntity<Map<String, Object>> getAllCustomers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        int offset = page * size;
        List<Map<String, Object>> customers = jdbcTemplate.queryForList(
                "SELECT customer_id, first_name, last_name, mobile_number, email, " +
                "national_id, verification_status, registration_channel, created_at " +
                "FROM customers ORDER BY customer_id ASC LIMIT ? OFFSET ?",
                size, offset);
        Long total = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM customers", Long.class);
        int totalPages = (int) Math.ceil((double) (total != null ? total : 0) / size);
        return ResponseEntity.ok(Map.of(
                "content", customers,
                "pageNumber", page,
                "pageSize", size,
                "totalElements", total != null ? total : 0,
                "totalPages", totalPages,
                "last", (page + 1) >= totalPages));
    }

    @GetMapping("/search")
    @Operation(summary = "Search customers by ID, name, or phone")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER')")
    public ResponseEntity<java.util.List<Map<String, Object>>> searchCustomers(
            @RequestParam(name = "q", defaultValue = "") String query) {
        String likeQuery = "%" + query + "%";
        Long idQuery = null;
        try { idQuery = Long.parseLong(query); } catch (Exception ignored) {}

        String sql = "SELECT c.customer_id as id, c.first_name || ' ' || c.last_name as name, " +
                "c.mobile_number as phone, 'General' as sector, " +
                "COALESCE(cse.final_score, 0) as score, " +
                "COALESCE(cse.pd_probability, 0.0) as pd " +
                "FROM customers c " +
                "LEFT JOIN (SELECT DISTINCT ON (customer_id) customer_id, final_score, pd_probability " +
                "           FROM credit_score_events ORDER BY customer_id, scored_at DESC) cse " +
                "ON c.customer_id = cse.customer_id " +
                "WHERE ? = '' OR c.first_name ILIKE ? OR c.last_name ILIKE ? OR c.mobile_number ILIKE ? " +
                "OR c.customer_id = ? " +
                "ORDER BY c.customer_id ASC LIMIT 50";

        var results = jdbcTemplate.queryForList(sql, query, likeQuery, likeQuery, likeQuery,
                idQuery != null ? idQuery : -1L);
        return ResponseEntity.ok(results);
    }

    // ──────────────────────────────────────────────────────────────
    // CREATE
    // ──────────────────────────────────────────────────────────────

    @PostMapping
    @Operation(summary = "Create a new customer (status: PENDING, awaiting maker-checker approval)")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST')")
    public ResponseEntity<Map<String, Object>> createCustomer(
            @RequestBody CustomerRequest request,
            Authentication auth) {
        String createdBy = auth != null ? auth.getName() : "system";
        jdbcTemplate.update(
                "INSERT INTO customers (first_name, last_name, mobile_number, email, national_id, " +
                "date_of_birth, gender, county, region, bank_name, account_number, " +
                "verification_status, crb_consent, registration_channel, created_by) " +
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,'PENDING',false,?,?)",
                request.getFirstName(), request.getLastName(), request.getMobileNumber(),
                request.getEmail(), request.getNationalId(),
                request.getDateOfBirth() != null ? request.getDateOfBirth().toString() : null,
                request.getGender(),
                request.getCounty(), request.getRegion(),
                request.getBankName(), request.getAccountNumber(),
                request.getRegistrationChannel() != null ? request.getRegistrationChannel() : "ADMIN_PORTAL",
                createdBy);

        Map<String, Object> saved = jdbcTemplate.queryForMap(
                "SELECT * FROM customers WHERE mobile_number = ? ORDER BY created_at DESC LIMIT 1",
                request.getMobileNumber());
        log.info("[CUSTOMER] Created customer={}, by={}", saved.get("customer_id"), createdBy);
        return ResponseEntity.ok(saved);
    }

    // ──────────────────────────────────────────────────────────────
    // READ / UPDATE PROFILE
    // ──────────────────────────────────────────────────────────────

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
                    "c.created_by, c.approved_by, c.approved_at, c.rejection_reason, " +
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
            return ResponseEntity.status(404).body(Map.of("error", "Customer not found", "customer_id", customerId));
        }
    }

    @PutMapping("/{customerId}")
    @Operation(summary = "Update customer profile")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST')")
    public ResponseEntity<Map<String, Object>> updateProfile(
            @PathVariable Long customerId,
            @RequestBody Map<String, Object> updates,
            Authentication auth) {
        log.info("Profile update: customer={}, by={}", customerId, auth.getName());
        _publishEvent("PROFILE_UPDATED", customerId, updates, auth.getName());
        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "updated_fields", updates.keySet(),
                "updated_at", LocalDateTime.now().toString()));
    }

    // ──────────────────────────────────────────────────────────────
    // MAKER-CHECKER: APPROVE / REJECT
    // ──────────────────────────────────────────────────────────────

    @PutMapping("/{customerId}/approve")
    @Operation(summary = "Approve a PENDING customer (checker step — cannot be the same user who created)")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST')")
    public ResponseEntity<Map<String, Object>> approveCustomer(
            @PathVariable Long customerId,
            @RequestBody(required = false) Map<String, String> body,
            Authentication auth) {
        String checkerUsername = auth.getName();

        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT created_by FROM customers WHERE customer_id = ?", customerId);
        if (rows.isEmpty()) {
            throw new RuntimeException("Customer not found: " + customerId);
        }
        String createdBy = (String) rows.get(0).get("created_by");
        if (createdBy != null && createdBy.equals(checkerUsername)) {
            throw new RuntimeException("Maker-checker segregation required: cannot approve a customer you created.");
        }

        jdbcTemplate.update(
                "UPDATE customers SET verification_status = 'APPROVED', approved_by = ?, approved_at = NOW() " +
                "WHERE customer_id = ?",
                checkerUsername, customerId);

        log.info("[MAKER-CHECKER] Customer {} approved by {}", customerId, checkerUsername);
        _publishEvent("CUSTOMER_APPROVED", customerId, Map.of("approvedBy", checkerUsername), checkerUsername);

        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "status", "APPROVED",
                "approved_by", checkerUsername,
                "approved_at", LocalDateTime.now().toString()));
    }

    @PutMapping("/{customerId}/reject")
    @Operation(summary = "Reject a PENDING customer (checker step — cannot be the same user who created)")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST')")
    public ResponseEntity<Map<String, Object>> rejectCustomer(
            @PathVariable Long customerId,
            @RequestBody Map<String, String> body,
            Authentication auth) {
        String checkerUsername = auth.getName();
        String reason = body.getOrDefault("reason", "");

        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT created_by FROM customers WHERE customer_id = ?", customerId);
        if (rows.isEmpty()) {
            throw new RuntimeException("Customer not found: " + customerId);
        }
        String createdBy = (String) rows.get(0).get("created_by");
        if (createdBy != null && createdBy.equals(checkerUsername)) {
            throw new RuntimeException("Maker-checker segregation required: cannot reject a customer you created.");
        }

        jdbcTemplate.update(
                "UPDATE customers SET verification_status = 'REJECTED', approved_by = ?, " +
                "approved_at = NOW(), rejection_reason = ? WHERE customer_id = ?",
                checkerUsername, reason, customerId);

        log.info("[MAKER-CHECKER] Customer {} rejected by {}, reason: {}", customerId, checkerUsername, reason);
        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "status", "REJECTED",
                "rejection_reason", reason,
                "rejected_by", checkerUsername));
    }

    // ──────────────────────────────────────────────────────────────
    // DISPUTES
    // ──────────────────────────────────────────────────────────────

    @GetMapping("/{customerId}/disputes")
    @Operation(summary = "List all disputes for a customer")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','VIEWER','CUSTOMER')")
    public ResponseEntity<Map<String, Object>> getDisputes(@PathVariable Long customerId) {
        var disputes = jdbcTemplate.queryForList(
                "SELECT dispute_id as id, COALESCE(disputed_field, reason) as field, " +
                "reason as desc, status, CAST(created_at AS DATE) as filed " +
                "FROM disputes WHERE customer_id = ? ORDER BY created_at DESC",
                customerId);
        return ResponseEntity.ok(Map.of("customer_id", customerId, "disputes", disputes));
    }

    @PostMapping("/{customerId}/disputes")
    @Operation(summary = "File a credit report dispute")
    @PreAuthorize("hasAnyRole('ADMIN','CUSTOMER')")
    public ResponseEntity<Map<String, Object>> fileDispute(
            @PathVariable Long customerId,
            @RequestBody Map<String, String> body,
            Authentication auth) {
        String description = body.getOrDefault("description", "");
        String field = body.getOrDefault("disputed_field", "");
        log.info("Dispute filed: customer={}, field={}", customerId, field);

        // Persist dispute to DB
        jdbcTemplate.update(
                "INSERT INTO disputes (customer_id, reason, disputed_field, status) VALUES (?, ?, ?, 'OPEN')",
                customerId, description, field.isEmpty() ? null : field);

        // Fetch the newly created dispute_id
        Long disputeDbId = jdbcTemplate.queryForObject(
                "SELECT dispute_id FROM disputes WHERE customer_id = ? ORDER BY created_at DESC LIMIT 1",
                Long.class, customerId);
        String disputeId = "DSP-" + (disputeDbId != null ? disputeDbId : UUID.randomUUID().toString().substring(0, 8).toUpperCase());

        rabbitTemplate.convertAndSend("athena.exchange", "athena.notification.routingKey",
                Map.of("type", "DISPUTE_FILED", "disputeId", disputeId,
                        "customerId", customerId, "field", field, "description", description,
                        "filedAt", LocalDateTime.now().toString()));
        return ResponseEntity.ok(Map.of(
                "dispute_id", disputeId, "customer_id", customerId, "status", "OPEN",
                "disputed_field", field, "filed_at", LocalDateTime.now().toString(),
                "message", "Dispute filed. Our team will review within 5 business days."));
    }

    // ──────────────────────────────────────────────────────────────
    // CONSENT
    // ──────────────────────────────────────────────────────────────

    @PutMapping("/{customerId}/consent")
    @Operation(summary = "Customer grants data access consent to a partner")
    @PreAuthorize("hasAnyRole('ADMIN','CUSTOMER')")
    public ResponseEntity<Map<String, Object>> grantConsent(
            @PathVariable Long customerId,
            @RequestBody Map<String, String> body,
            Authentication auth) {
        String partnerId = body.getOrDefault("partner_id", "unknown");
        String scope = body.getOrDefault("scope", "CREDIT_SCORE");
        String consentToken = UUID.randomUUID().toString();
        long partnerIdLong = Math.abs((long) partnerId.hashCode());
        jdbcTemplate.update(
                "INSERT INTO consents (customer_id, partner_id, scope, token_jti, expires_at) " +
                "VALUES (?, ?, ?, ?, NOW() + INTERVAL '1 year') ON CONFLICT (token_jti) DO NOTHING",
                customerId, partnerIdLong, scope, consentToken);
        _publishEvent("CONSENT_GRANTED", customerId, Map.of("partner_id", partnerId, "scope", scope), auth.getName());
        return ResponseEntity.ok(Map.of(
                "consent_token", consentToken, "customer_id", customerId,
                "partner_id", partnerId, "scope", scope,
                "expires_at", LocalDateTime.now().plusYears(1).toString()));
    }

    // ──────────────────────────────────────────────────────────────
    // CONSENTS
    // ──────────────────────────────────────────────────────────────

    @GetMapping("/{customerId}/consents")
    @Operation(summary = "List active consents for a customer")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST','CUSTOMER')")
    public ResponseEntity<java.util.List<Map<String, Object>>> getConsents(@PathVariable Long customerId) {
        var consents = jdbcTemplate.queryForList(
                "SELECT consent_id as id, " +
                "CASE partner_id " +
                "  WHEN 1178866990 THEN 'KCB Bank' " +
                "  WHEN 492889783  THEN 'Equity Bank' " +
                "  WHEN 1069688314 THEN 'Co-operative Bank' " +
                "  WHEN 723158978  THEN 'Safaricom M-Pesa' " +
                "  WHEN 327945913  THEN 'Standard Chartered' " +
                "  WHEN 1894859336 THEN 'NCBA Bank' " +
                "  WHEN 1188602069 THEN 'Absa Kenya' " +
                "  WHEN 1709023242 THEN 'DTB Bank' " +
                "  WHEN 1558763374 THEN 'Stanbic Bank' " +
                "  WHEN 609826168  THEN 'Family Bank' " +
                "  ELSE CAST(partner_id AS VARCHAR) END as name, " +
                "scope, CAST(created_at AS DATE) as granted " +
                "FROM consents WHERE customer_id = ? AND revoked = false " +
                "ORDER BY created_at DESC",
                customerId);
        return ResponseEntity.ok(consents);
    }

    @DeleteMapping("/{customerId}/consents/{consentId}")
    @Operation(summary = "Revoke a specific consent by consent_id")
    @PreAuthorize("hasAnyRole('ADMIN','CUSTOMER')")
    public ResponseEntity<Map<String, Object>> revokeConsent(
            @PathVariable Long customerId,
            @PathVariable Long consentId,
            Authentication auth) {
        int updated = jdbcTemplate.update(
                "UPDATE consents SET revoked = true WHERE customer_id = ? AND consent_id = ?",
                customerId, consentId);
        log.info("[CONSENT] Revoked: customer={}, consentId={}, rows={}", customerId, consentId, updated);
        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "consent_id", consentId,
                "revoked", updated > 0));
    }

    // ──────────────────────────────────────────────────────────────
    // IDENTITY DOCUMENT
    // ──────────────────────────────────────────────────────────────

    @PutMapping("/{customerId}/identity-document")
    @Operation(summary = "Link an uploaded document to a customer (validates via media-service)")
    @PreAuthorize("hasAnyRole('ADMIN','ANALYST')")
    public ResponseEntity<Map<String, Object>> updateIdentityDocument(
            @PathVariable Long customerId,
            @RequestParam UUID documentId,
            Authentication auth) {
        try {
            var media = mediaClient.getMediaMetadata(documentId);
            log.info("[CUSTOMER] Media validated: id={}, file={}", documentId, media.getOriginalFilename());
        } catch (Exception e) {
            log.error("[CUSTOMER] Failed to validate media id={}: {}", documentId, e.getMessage());
            throw new RuntimeException("Invalid document ID. Media not found in media-service.");
        }

        jdbcTemplate.update(
                "UPDATE customers SET identity_document_id = ? WHERE customer_id = ?",
                documentId, customerId);

        log.info("[CUSTOMER] Identity document {} linked to customer {}", documentId, customerId);
        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "document_id", documentId.toString(),
                "linked_by", auth.getName(),
                "linked_at", LocalDateTime.now().toString()));
    }

    // ──────────────────────────────────────────────────────────────
    // CSV WHITELIST UPLOAD
    // ──────────────────────────────────────────────────────────────

    @PostMapping("/whitelist")
    @Operation(summary = "Bulk whitelist customers via CSV (auto-approved)",
               description = "CSV columns: name, phoneNumber, email, nationalId, gender, dateOfBirth (YYYY-MM-DD)")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> uploadWhitelist(
            @RequestParam("file") MultipartFile file,
            Authentication auth) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Empty file", "message", "Please upload a valid CSV file."));
        }

        List<String> processed = new ArrayList<>();
        List<String> skipped = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8));
             CSVParser csvParser = new CSVParser(reader,
                     CSVFormat.DEFAULT.withFirstRecordAsHeader().withIgnoreHeaderCase().withTrim())) {

            for (CSVRecord record : csvParser) {
                String phone = record.get("phoneNumber");
                Integer exists = jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM customers WHERE mobile_number = ?", Integer.class, phone);
                if (exists != null && exists > 0) {
                    skipped.add(phone);
                    continue;
                }

                String name = record.get("name");
                String[] nameParts = name.split(" ", 2);
                String firstName = nameParts[0];
                String lastName = nameParts.length > 1 ? nameParts[1] : "";

                String dobStr = record.isMapped("dateOfBirth") ? record.get("dateOfBirth") : null;
                LocalDate dob = null;
                try { if (dobStr != null) dob = LocalDate.parse(dobStr); } catch (Exception ignored) {}

                String gender = record.isMapped("gender") ? record.get("gender").toUpperCase() : "MALE";
                String nationalId = record.isMapped("nationalId") ? record.get("nationalId") : null;
                String email = record.isMapped("email") ? record.get("email") : null;

                jdbcTemplate.update(
                        "INSERT INTO customers (first_name, last_name, mobile_number, email, national_id, " +
                        "date_of_birth, gender, verification_status, crb_consent, registration_channel, created_by) " +
                        "VALUES (?,?,?,?,?,?,?,'APPROVED',true,'PARTNER_API',?)",
                        firstName, lastName, phone, email, nationalId,
                        dob != null ? dob.toString() : null, gender, auth.getName());
                processed.add(phone);
            }

        } catch (Exception e) {
            log.error("[CUSTOMER] CSV whitelist processing failed: {}", e.getMessage());
            throw new RuntimeException("Failed to parse CSV: " + e.getMessage());
        }

        log.info("[CUSTOMER] Whitelist CSV: processed={}, skipped={}", processed.size(), skipped.size());
        return ResponseEntity.ok(Map.of(
                "processed", processed.size(),
                "skipped", skipped.size(),
                "skipped_phones", skipped,
                "message", "Whitelist upload completed successfully."));
    }

    // ──────────────────────────────────────────────────────────────
    // INTERNAL HELPERS
    // ──────────────────────────────────────────────────────────────

    private void _publishEvent(String type, Long customerId, Object payload, String actor) {
        try {
            rabbitTemplate.convertAndSend("athena.exchange", "athena.scoring.routingKey",
                    Map.of("type", type, "customerId", customerId, "payload", payload,
                            "actor", actor, "ts", LocalDateTime.now().toString()));
        } catch (Exception e) {
            log.error("Event publish failed: {}", e.getMessage());
        }
    }
}
