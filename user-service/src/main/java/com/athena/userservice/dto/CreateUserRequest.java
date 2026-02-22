package com.athena.userservice.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.util.Set;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Schema(description = "Request to create a new internal user (Admin only)")
public class CreateUserRequest {

    @Schema(description = "Username", example = "analyst_john")
    private String username;

    @Schema(description = "Password", example = "SecurePass@123")
    private String password;

    @Schema(description = "First name", example = "John")
    private String firstName;

    @Schema(description = "Last name", example = "Doe")
    private String lastName;

    @Schema(description = "Email address", example = "john.doe@athena.co.ke")
    private String email;

    @Schema(description = "Role names to assign", example = "[\"ANALYST\"]")
    private Set<String> roles;

    @Schema(description = "Group names to assign", example = "[\"ANALYSTS\"]")
    private Set<String> groups;
}
