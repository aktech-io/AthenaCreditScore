package com.athena.notificationservice.service;

import com.athena.notificationservice.model.NotificationConfig;
import com.athena.notificationservice.model.NotificationLog;
import com.athena.notificationservice.repository.NotificationConfigRepository;
import com.athena.notificationservice.repository.NotificationLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import org.springframework.stereotype.Service;

import java.util.Properties;

@Service
@RequiredArgsConstructor
@Slf4j
public class NotificationService {

    private final NotificationConfigRepository configRepository;
    private final NotificationLogRepository logRepository;

    // -------------------------------------------------------------------------
    // Core email dispatcher — used by all event-driven and REST-triggered sends
    // -------------------------------------------------------------------------

    public void sendEmail(String serviceName, String to, String subject, String body) {
        log.info("[{}] Sending email to: {} subject: '{}'", serviceName, to, subject);
        String status = "FAILED";
        String errorMsg = null;

        try {
            NotificationConfig config = configRepository.findByType("EMAIL")
                    .orElseThrow(() -> new RuntimeException("Email configuration not found"));

            if (!config.isEnabled()) {
                log.warn("Email notifications are DISABLED. Skipping send to {}", to);
                status = "SKIPPED";
                return;
            }

            JavaMailSenderImpl mailSender = new JavaMailSenderImpl();
            mailSender.setHost(config.getHost());
            mailSender.setPort(config.getPort());
            mailSender.setUsername(config.getUsername());
            mailSender.setPassword(config.getPassword());

            Properties props = mailSender.getJavaMailProperties();
            props.put("mail.transport.protocol", "smtp");
            props.put("mail.smtp.auth", "true");

            if (config.getPort() == 465) {
                props.put("mail.smtp.ssl.enable", "true");
                props.put("mail.smtp.ssl.trust", "*");
                props.put("mail.smtp.socketFactory.port", "465");
                props.put("mail.smtp.socketFactory.class", "javax.net.ssl.SSLSocketFactory");
                props.put("mail.smtp.socketFactory.fallback", "false");
            } else {
                props.put("mail.smtp.starttls.enable", "true");
                props.put("mail.smtp.starttls.required", "true");
                props.put("mail.smtp.ssl.trust", "*");
            }

            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(config.getFromAddress());
            message.setTo(to);
            message.setSubject(subject);
            message.setText(body);

            mailSender.send(message);
            log.info("Email sent successfully to {}", to);
            status = "SENT";

        } catch (Exception e) {
            log.error("Failed to send email to {}: {}", to, e.getMessage());
            errorMsg = e.getMessage();
            if (!"SKIPPED".equals(status)) {
                throw new RuntimeException("Failed to send email: " + e.getMessage());
            }
        } finally {
            logRepository.save(NotificationLog.builder()
                    .serviceName(serviceName)
                    .type("EMAIL")
                    .recipient(to)
                    .subject(subject)
                    .body(body)
                    .status(status)
                    .errorMessage(errorMsg)
                    .build());
        }
    }

    // -------------------------------------------------------------------------
    // Athena Credit Score — event-driven email templates
    // -------------------------------------------------------------------------

    public void sendDisputeAcknowledgement(String to, String disputeId, Long customerId) {
        String subject = "Dispute Received — Athena Credit Score";
        String body = String.format(
                "Dear Valued Customer,\n\n" +
                "We have received your credit report dispute (Ref: %s).\n\n" +
                "Our team will review your dispute and respond within 5 working days in accordance " +
                "with the Credit Reference Bureau Regulations, 2013.\n\n" +
                "You can track the status of your dispute by logging into the Athena Customer Portal.\n\n" +
                "Regards,\n" +
                "Athena Credit Score Team\n" +
                "support@athena.co.ke",
                disputeId);
        sendEmail("customer-service", to, subject, body);
    }

    public void sendScoreUpdateNotification(String to, Object score, Long customerId) {
        String subject = "Your Credit Score Has Been Updated — Athena";
        String body = String.format(
                "Dear Valued Customer,\n\n" +
                "Your Athena Credit Score has been updated.\n\n" +
                "New Score: %s / 850\n\n" +
                "Log in to the Athena Customer Portal to view your full credit report " +
                "and understand what factors influenced your score.\n\n" +
                "Regards,\n" +
                "Athena Credit Score Team\n" +
                "support@athena.co.ke",
                score);
        sendEmail("scoring-service", to, subject, body);
    }

    public void sendConsentGrantedNotification(String to, Object partnerId, Long customerId) {
        String subject = "Data Access Consent Confirmed — Athena";
        String body = String.format(
                "Dear Valued Customer,\n\n" +
                "You have successfully granted data access consent to partner: %s.\n\n" +
                "If you did not authorise this, please contact us immediately at support@athena.co.ke " +
                "or call +254 700 000 000.\n\n" +
                "You can revoke consent at any time from the Athena Customer Portal.\n\n" +
                "Regards,\n" +
                "Athena Credit Score Team",
                partnerId);
        sendEmail("customer-service", to, subject, body);
    }

    // -------------------------------------------------------------------------
    // Config management
    // -------------------------------------------------------------------------

    public NotificationConfig getConfig(String type) {
        return configRepository.findByType(type).orElse(null);
    }

    public NotificationConfig updateConfig(NotificationConfig config) {
        NotificationConfig existing = configRepository.findByType(config.getType())
                .orElse(config);

        existing.setProvider(config.getProvider());
        existing.setHost(config.getHost());
        existing.setPort(config.getPort());
        existing.setUsername(config.getUsername());
        existing.setPassword(config.getPassword());
        existing.setFromAddress(config.getFromAddress());
        existing.setApiKey(config.getApiKey());
        existing.setApiSecret(config.getApiSecret());
        existing.setSenderId(config.getSenderId());
        existing.setEnabled(config.isEnabled());
        existing.setType(config.getType());

        return configRepository.save(existing);
    }
}
