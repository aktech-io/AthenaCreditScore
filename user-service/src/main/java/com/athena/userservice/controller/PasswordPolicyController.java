package com.athena.userservice.controller;

import com.athena.userservice.model.PasswordPolicy;
import com.athena.userservice.service.PasswordPolicyService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/admin/password-policy")
@RequiredArgsConstructor
@Tag(name = "Password Policy", description = "Admin endpoints for configuring password security policy")
public class PasswordPolicyController {

    private final PasswordPolicyService passwordPolicyService;

    @GetMapping
    @Operation(summary = "Get current password policy")
    public ResponseEntity<PasswordPolicy> getPolicy() {
        return ResponseEntity.ok(passwordPolicyService.getCurrentPolicy());
    }

    @PutMapping
    @Operation(summary = "Update password policy")
    public ResponseEntity<PasswordPolicy> updatePolicy(@RequestBody PasswordPolicy policy) {
        return ResponseEntity.ok(passwordPolicyService.updatePolicy(policy));
    }
}
