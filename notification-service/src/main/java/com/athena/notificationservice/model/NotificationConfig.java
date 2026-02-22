package com.athena.notificationservice.model;

import jakarta.persistence.*;
import lombok.*;

@Data
@Entity
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "notification_configs")
public class NotificationConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String type; // EMAIL, SMS

    private String provider; // e.g., SMTP, AFRICAS_TALKING

    // Email (SMTP) settings
    private String host;
    private int port;
    private String username;
    private String password;
    private String fromAddress;

    // SMS / Africa's Talking settings
    private String apiKey;
    private String apiSecret;
    private String senderId;

    private boolean enabled;
}
