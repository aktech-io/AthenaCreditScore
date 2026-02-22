package com.athena.userservice.dto;

import lombok.*;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthResponse {
    private String token;
    private String username;
    private String firstName;
    private String lastName;
    private String email;
    private List<String> roles;
    private List<String> groups;
    private Long customerId;
}
