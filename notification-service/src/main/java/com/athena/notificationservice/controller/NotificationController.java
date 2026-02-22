package com.athena.notificationservice.controller;

import com.athena.notificationservice.dto.NotificationRequest;
import com.athena.notificationservice.model.NotificationConfig;
import com.athena.notificationservice.service.NotificationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/notifications")
@RequiredArgsConstructor
@Tag(name = "Notifications", description = "Notification configuration and manual send endpoints")
public class NotificationController {

    private final NotificationService notificationService;

    @GetMapping("/config/{type}")
    @Operation(summary = "Get notification config for EMAIL or SMS")
    public ResponseEntity<NotificationConfig> getConfig(@PathVariable String type) {
        return ResponseEntity.ok(notificationService.getConfig(type.toUpperCase()));
    }

    @PostMapping("/config")
    @Operation(summary = "Create or update notification config")
    public ResponseEntity<NotificationConfig> updateConfig(@RequestBody NotificationConfig config) {
        return ResponseEntity.ok(notificationService.updateConfig(config));
    }

    @PostMapping("/send")
    @Operation(summary = "Send a notification manually")
    public ResponseEntity<String> send(@RequestBody NotificationRequest request) {
        if (request.getType() == NotificationRequest.NotificationType.EMAIL) {
            notificationService.sendEmail(
                    request.getServiceName() != null ? request.getServiceName() : "api",
                    request.getRecipient(),
                    request.getSubject(),
                    request.getMessage());
            return ResponseEntity.ok("Email queued");
        } else if (request.getType() == NotificationRequest.NotificationType.SMS) {
            // Africa's Talking SMS integration — future implementation
            return ResponseEntity.ok("SMS not yet implemented");
        }
        return ResponseEntity.badRequest().body("Unsupported notification type");
    }
}
