package com.athena.creditscore.dto;

import lombok.*;
import jakarta.validation.constraints.NotBlank;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthRequest {
    @NotBlank private String username;
    @NotBlank private String password;
    private String firstName;
    private String lastName;
    private String email;
    private String totpCode;  // For admin 2FA
}
