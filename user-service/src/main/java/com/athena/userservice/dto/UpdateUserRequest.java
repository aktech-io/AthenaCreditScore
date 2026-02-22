package com.athena.userservice.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.util.Set;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Schema(description = "Request to update an existing user")
public class UpdateUserRequest {

    @Schema(description = "New password (leave null to keep unchanged)")
    private String password;

    @Schema(description = "First name")
    private String firstName;

    @Schema(description = "Last name")
    private String lastName;

    @Schema(description = "Email address")
    private String email;

    @Schema(description = "Role names (replaces existing)")
    private Set<String> roles;

    @Schema(description = "Group names (replaces existing)")
    private Set<String> groups;
}
