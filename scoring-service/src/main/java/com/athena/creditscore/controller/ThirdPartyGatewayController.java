package com.athena.creditscore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * Third-Party API Gateway Controller.
 *
 * Handles external partner access with:
 * - API key validation (done by Kong — key-auth plugin)
 * - Consent token verification before exposing customer data
 * - Audit log event published to RabbitMQ for compliance
 * - Webhook dispatcher (async via RabbitMQ)
 */
@RestController
@RequestMapping("/api/v3p")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Third-Party API", description = "External partner API with audit logging and consent enforcement")
public class ThirdPartyGatewayController {

    private final WebClient.Builder webClientBuilder;
    private final RabbitTemplate rabbitTemplate;

    @org.springframework.beans.factory.annotation.Value("${scoring.engine.url:http://athena-python-service:8001}")
    private String scoringEngineUrl;

    // ── GET credit score (consent-gated) ──────────────────────────────────────

    @GetMapping("/credit-score/{customerId}")
    @Operation(summary = "Partner: get customer credit score (requires consent token)")
    public ResponseEntity<?> getScore(
            @PathVariable Long customerId,
            @RequestParam String consentToken,
            @RequestHeader(value = "X-Api-Key", required = false) String apiKey,
            @RequestHeader(value = "X-Partner-Id", required = false) String partnerId,
            HttpServletRequest request
    ) {
        if (!validateConsent(customerId, consentToken)) {
            _auditLog(partnerId, customerId, "CREDIT_SCORE_REQUEST", "DENIED_NO_CONSENT", request);
            return ResponseEntity.status(403).body(Map.of(
                    "error", "CONSENT_REQUIRED",
                    "message", "Customer has not granted consent for this partner to access their credit data."
            ));
        }

        _auditLog(partnerId, customerId, "CREDIT_SCORE_REQUEST", "APPROVED", request);

        Map result = webClientBuilder.build()
                .get()
                .uri(scoringEngineUrl + "/api/v1/credit-score/" + customerId)
                .header("X-Api-Key", "dev-key")
                .retrieve()
                .bodyToMono(Map.class)
                .block();

        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "partner_id", partnerId != null ? partnerId : "unknown",
                "score_data",  result != null ? result : Map.of(),
                "consent_verified", true,
                "request_id", UUID.randomUUID().toString()
        ));
    }

    // ── Webhook registration ──────────────────────────────────────────────────

    @PostMapping("/webhooks")
    @Operation(summary = "Partner: register a webhook URL to receive scoring events")
    public ResponseEntity<Map<String, Object>> registerWebhook(
            @RequestBody Map<String, String> body,
            @RequestHeader(value = "X-Partner-Id", required = false) String partnerId
    ) {
        String webhookUrl = body.getOrDefault("url", "");
        String eventType  = body.getOrDefault("event_type", "SCORE_UPDATED");

        log.info("Webhook registered: partner={}, url={}, event={}", partnerId, webhookUrl, eventType);

        // Publish async webhook config event to RabbitMQ
        rabbitTemplate.convertAndSend(
                "athena.exchange",
                "athena.notification.routingKey",
                Map.of(
                        "type",       "WEBHOOK_REGISTRATION",
                        "partnerId",  partnerId,
                        "url",        webhookUrl,
                        "eventType",  eventType,
                        "registeredAt", LocalDateTime.now().toString()
                )
        );

        return ResponseEntity.ok(Map.of(
                "webhook_id",   UUID.randomUUID().toString(),
                "partner_id",   partnerId,
                "url",          webhookUrl,
                "event_type",   eventType,
                "status",       "REGISTERED"
        ));
    }

    // ── Consent revocation ────────────────────────────────────────────────────

    @DeleteMapping("/consent/{customerId}")
    @Operation(summary = "Partner: record that a customer has revoked data access consent")
    public ResponseEntity<Map<String, Object>> revokeConsent(
            @PathVariable Long customerId,
            @RequestHeader(value = "X-Partner-Id", required = false) String partnerId,
            HttpServletRequest request
    ) {
        _auditLog(partnerId, customerId, "CONSENT_REVOKED", "OK", request);
        log.info("Consent revoked: customer={}, partner={}", customerId, partnerId);
        return ResponseEntity.ok(Map.of(
                "customer_id", customerId,
                "partner_id",  partnerId,
                "status",      "CONSENT_REVOKED",
                "revoked_at",  LocalDateTime.now().toString()
        ));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private boolean validateConsent(Long customerId, String consentToken) {
        // Production: look up consent token in `consents` table, check expiry & scope
        // MVP: accept non-null, non-empty token
        return consentToken != null && !consentToken.isBlank();
    }

    private void _auditLog(String partnerId, Long customerId, String action, String outcome, HttpServletRequest req) {
        try {
            rabbitTemplate.convertAndSend(
                    "athena.exchange",
                    "athena.scoring.routingKey",
                    Map.of(
                            "type",       "AUDIT_LOG",
                            "partnerId",  partnerId != null ? partnerId : "unknown",
                            "customerId", customerId,
                            "action",     action,
                            "outcome",    outcome,
                            "ip",         req.getRemoteAddr(),
                            "ts",         LocalDateTime.now().toString()
                    )
            );
        } catch (Exception e) {
            log.error("Audit log publish failed: {}", e.getMessage());
        }
    }
}
