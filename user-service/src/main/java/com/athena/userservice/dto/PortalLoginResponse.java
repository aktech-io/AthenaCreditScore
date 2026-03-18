package com.athena.userservice.dto;

import lombok.*;

/**
 * Login response format expected by qena-connect portal.
 * Wraps the authenticated user's details under a nested "user" field.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PortalLoginResponse {
    private String token;
    private UserInfo user;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserInfo {
        private String id;
        private String email;
        private String firstName;
        private String lastName;
        private String role;          // "CUSTOMER", "ADMIN", "MERCHANT"
        private String customerId;    // String form of numeric customer_id, null for admin
        private String merchantId;    // null unless merchant role
    }
}
