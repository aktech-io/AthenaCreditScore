package com.athena.notificationservice.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "notification_logs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String serviceName;

    @Column(nullable = false)
    private String type; // EMAIL, SMS

    @Column(nullable = false)
    private String recipient;

    private String subject;

    @Column(columnDefinition = "TEXT")
    private String body;

    @Column(nullable = false)
    private String status; // SENT, FAILED, SKIPPED

    @Column(columnDefinition = "TEXT")
    private String errorMessage;

    @CreationTimestamp
    private LocalDateTime sentAt;
}
