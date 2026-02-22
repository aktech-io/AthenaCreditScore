package com.athena.userservice.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "admin_users")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String username;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @Column(name = "first_name")
    private String firstName;

    @Column(name = "last_name")
    private String lastName;

    @Column
    private String email;

    /** Role: ADMIN | ANALYST | VIEWER | CREDIT_RISK */
    @Column(nullable = false)
    private String role;

    @Column(name = "totp_secret")
    private String totpSecret;

    @Column(name = "is_active", nullable = false)
    @Builder.Default
    private boolean active = true;
}
