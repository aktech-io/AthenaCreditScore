package com.athena.notificationservice.listener;

import com.athena.notificationservice.service.NotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class AthenaEventListener {

    private final NotificationService notificationService;

    @RabbitListener(queues = "athena.notification.queue")
    public void handleNotificationEvent(Map<String, Object> event) {
        String type = (String) event.getOrDefault("type", "UNKNOWN");
        Object customerIdObj = event.get("customerId");
        Long customerId = customerIdObj instanceof Number n ? n.longValue() : null;
        String email = (String) event.get("email");

        log.info("[NOTIFICATION] type={} customerId={}", type, customerId);

        switch (type) {
            case "DISPUTE_FILED" -> {
                String disputeId = (String) event.get("disputeId");
                log.info("[NOTIFICATION] Dispute {} filed for customer {}", disputeId, customerId);
                if (email != null) {
                    notificationService.sendDisputeAcknowledgement(email, disputeId, customerId);
                } else {
                    log.warn("[NOTIFICATION] No email in event payload for DISPUTE_FILED customerId={}", customerId);
                }
            }
            case "SCORE_UPDATED" -> {
                Object score = event.get("score");
                log.info("[NOTIFICATION] Score updated for customer {} → {}", customerId, score);
                if (email != null) {
                    notificationService.sendScoreUpdateNotification(email, score, customerId);
                } else {
                    log.warn("[NOTIFICATION] No email in event payload for SCORE_UPDATED customerId={}", customerId);
                }
            }
            case "CONSENT_GRANTED" -> {
                Object partnerId = event.get("partnerId");
                log.info("[NOTIFICATION] Consent granted by customer {} to partner {}", customerId, partnerId);
                if (email != null) {
                    notificationService.sendConsentGrantedNotification(email, partnerId, customerId);
                } else {
                    log.warn("[NOTIFICATION] No email in event payload for CONSENT_GRANTED customerId={}", customerId);
                }
            }
            case "USER_INVITATION" -> {
                String token = (String) event.get("token");
                log.info("[NOTIFICATION] User invitation for {}", email);
                if (email != null && token != null) {
                    String subject = "You've been invited to Athena Credit Score Platform";
                    String body = String.format(
                            "Hello,\n\n" +
                            "You have been invited to join the Athena Credit Score Platform.\n\n" +
                            "Complete your registration here:\n" +
                            "http://localhost:5173/complete-registration?token=%s\n\n" +
                            "This link expires in 24 hours.\n\n" +
                            "Regards,\nAthena Team", token);
                    notificationService.sendEmail("user-service", email, subject, body);
                } else {
                    log.warn("[NOTIFICATION] Missing email or token in USER_INVITATION event");
                }
            }
            default -> log.warn("[NOTIFICATION] Unknown event type: {}", type);
        }
    }

    @RabbitListener(queues = "athena.dispute.queue")
    public void handleDisputeEvent(Map<String, Object> event) {
        String type = (String) event.getOrDefault("type", "UNKNOWN");
        log.info("[DISPUTE-EVENT] type={} payload={}", type, event);
        // Routes to compliance team mailbox — configure via /api/v1/notifications/config
    }
}
