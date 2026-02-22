package com.athena.notificationservice.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Generic notification request")
public class NotificationRequest {

    @Schema(description = "Calling service name", example = "scoring-service")
    private String serviceName;

    @Schema(description = "Type of notification", allowableValues = {"EMAIL", "SMS"})
    private NotificationType type;

    @Schema(description = "Recipient identifier (email address or phone number)", example = "customer@example.com")
    private String recipient;

    @Schema(description = "Subject line (for emails)", example = "Your Athena Credit Score has been updated")
    private String subject;

    @Schema(description = "Message body content")
    private String message;

    @Schema(description = "Additional metadata for template processing")
    private Map<String, Object> metadata;

    public enum NotificationType {
        EMAIL,
        SMS,
        PUSH
    }
}
