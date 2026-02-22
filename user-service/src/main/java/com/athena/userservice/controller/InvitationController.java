package com.athena.userservice.controller;

import com.athena.userservice.model.Invitation;
import com.athena.userservice.model.User;
import com.athena.userservice.repository.InvitationRepository;
import com.athena.userservice.repository.UserRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.*;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Tag(name = "Invitation", description = "Public endpoints for accepting invitations and completing registration")
public class InvitationController {

    private final InvitationRepository invitationRepository;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @GetMapping("/validate-token")
    @Operation(summary = "Validate invitation token")
    public ResponseEntity<?> validateToken(@RequestParam String token) {
        Invitation invitation = invitationRepository.findByToken(token)
                .orElseThrow(() -> new RuntimeException("Invalid token"));

        if (invitation.isUsed()) {
            return ResponseEntity.badRequest().body("Token already used");
        }
        if (invitation.getExpiryDate().isBefore(LocalDateTime.now())) {
            return ResponseEntity.badRequest().body("Token expired");
        }

        return ResponseEntity.ok(new InvitationResponse(invitation.getEmail()));
    }

    @PostMapping("/complete-registration")
    @Operation(summary = "Complete registration via invitation token")
    public ResponseEntity<?> completeRegistration(@RequestBody CompleteRegistrationRequest request) {
        Invitation invitation = invitationRepository.findByToken(request.getToken())
                .orElseThrow(() -> new RuntimeException("Invalid token"));

        if (invitation.isUsed() || invitation.getExpiryDate().isBefore(LocalDateTime.now())) {
            return ResponseEntity.badRequest().body("Token invalid or expired");
        }

        User user = User.builder()
                .username(invitation.getEmail())
                .email(invitation.getEmail())
                .firstName(request.getFirstName())
                .lastName(request.getLastName())
                .password(passwordEncoder.encode(request.getPassword()))
                .status("ACTIVE")
                .roles(new java.util.HashSet<>(invitation.getRoles()))
                .groups(new java.util.HashSet<>(invitation.getGroups()))
                .build();

        userRepository.save(user);

        invitation.setUsed(true);
        invitationRepository.save(invitation);

        return ResponseEntity.ok("Registration completed successfully");
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    public static class InvitationResponse {
        private String email;
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    public static class CompleteRegistrationRequest {
        private String token;
        private String firstName;
        private String lastName;
        private String password;
    }
}
