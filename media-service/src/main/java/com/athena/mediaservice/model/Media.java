package com.athena.mediaservice.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "media_files")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Media {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = true)
    private UUID referenceId; // Generic reference ID (for non-customer entities)

    @Column(nullable = true)
    private Long customerId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private MediaCategory category;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private MediaType mediaType;

    @Column(nullable = false)
    private String originalFilename;

    @Column(nullable = false)
    private String storedFilename;

    @Column(nullable = false)
    private String contentType;

    private Long fileSize;

    private String uploadedBy;

    private String serviceName;

    private String channel;

    @Column(length = 500)
    private String tags; // Comma-separated tags for searchability

    @Column(columnDefinition = "TEXT")
    private String description;

    @Builder.Default
    @Column(nullable = false)
    private Boolean isPublic = false;

    private String thumbnail;

    @Enumerated(EnumType.STRING)
    @Builder.Default
    @Column(nullable = false)
    private MediaStatus status = MediaStatus.ACTIVE;

    @CreationTimestamp
    private LocalDateTime createdAt;

    public enum MediaCategory {
        CUSTOMER_DOCUMENT,
        USER_PROFILE,
        FINANCIAL,
        SYSTEM,
        OTHER
    }

    public enum MediaType {
        ID_FRONT, ID_BACK, PASSPORT, SELFIE, PROOF_OF_ADDRESS,
        PROFILE_PICTURE, SIGNATURE,
        RECEIPT, INVOICE, CONTRACT,
        OTHER
    }

    public enum MediaStatus {
        ACTIVE, ARCHIVED, DELETED
    }
}
