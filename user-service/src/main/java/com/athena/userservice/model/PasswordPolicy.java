package com.athena.userservice.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "password_policies")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PasswordPolicy {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private int minLength;

    @Column(nullable = false)
    private boolean requireUppercase;

    @Column(nullable = false)
    private boolean requireLowercase;

    @Column(nullable = false)
    private boolean requireNumbers;

    @Column(nullable = false)
    private boolean requireSpecialChars;

    @Column(nullable = false)
    private int expirationDays; // 0 = no expiration

    private String specialChars; // e.g. "!@#$%^&*"
}
