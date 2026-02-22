package com.athena.userservice.controller;

import com.athena.userservice.config.AthenaRabbitMQConfig;
import com.athena.userservice.dto.CreateUserRequest;
import com.athena.userservice.dto.UpdateUserRequest;
import com.athena.userservice.exception.UserAlreadyExistsException;
import com.athena.userservice.model.Group;
import com.athena.userservice.model.Role;
import com.athena.userservice.model.User;
import com.athena.userservice.repository.GroupRepository;
import com.athena.userservice.repository.InvitationRepository;
import com.athena.userservice.repository.RoleRepository;
import com.athena.userservice.repository.UserRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/admin/users")
@RequiredArgsConstructor
@Tag(name = "User Management", description = "Admin endpoints for managing internal users")
public class UserManagementController {

    private final UserRepository userRepository;
    private final GroupRepository groupRepository;
    private final RoleRepository roleRepository;
    private final InvitationRepository invitationRepository;
    private final PasswordEncoder passwordEncoder;
    private final RabbitTemplate rabbitTemplate;

    @GetMapping
    @Operation(summary = "List all internal users")
    public ResponseEntity<List<User>> getAllUsers() {
        return ResponseEntity.ok(userRepository.findAll());
    }

    @PostMapping
    @Operation(summary = "Create an internal user directly")
    public ResponseEntity<User> createUser(@RequestBody CreateUserRequest request) {
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            throw new UserAlreadyExistsException("User already exists: " + request.getUsername());
        }

        User user = User.builder()
                .username(request.getUsername())
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .firstName(request.getFirstName())
                .lastName(request.getLastName())
                .status("ACTIVE")
                .roles(new HashSet<>())
                .groups(new HashSet<>())
                .build();

        if (request.getRoles() != null) {
            request.getRoles().forEach(name -> roleRepository.findByName(name).ifPresent(user.getRoles()::add));
        }
        if (request.getGroups() != null) {
            request.getGroups().forEach(name -> groupRepository.findByName(name).ifPresent(user.getGroups()::add));
        }

        return ResponseEntity.ok(userRepository.save(user));
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update an internal user")
    public ResponseEntity<User> updateUser(@PathVariable Long id, @RequestBody UpdateUserRequest request) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("User not found: " + id));

        if (request.getPassword() != null && !request.getPassword().isEmpty()) {
            user.setPassword(passwordEncoder.encode(request.getPassword()));
        }
        if (request.getFirstName() != null) user.setFirstName(request.getFirstName());
        if (request.getLastName() != null)  user.setLastName(request.getLastName());
        if (request.getEmail() != null)     user.setEmail(request.getEmail());

        if (request.getRoles() != null) {
            user.getRoles().clear();
            request.getRoles().forEach(name -> {
                Role role = roleRepository.findByName(name)
                        .orElseThrow(() -> new RuntimeException("Role not found: " + name));
                user.getRoles().add(role);
            });
        }
        if (request.getGroups() != null) {
            user.getGroups().clear();
            request.getGroups().forEach(name -> {
                Group group = groupRepository.findByName(name)
                        .orElseThrow(() -> new RuntimeException("Group not found: " + name));
                user.getGroups().add(group);
            });
        }

        return ResponseEntity.ok(userRepository.save(user));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete an internal user")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        if (!userRepository.existsById(id)) throw new RuntimeException("User not found: " + id);
        userRepository.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{userId}/groups/{groupId}")
    @Operation(summary = "Assign user to a group")
    public ResponseEntity<User> assignToGroup(@PathVariable Long userId, @PathVariable Long groupId) {
        User user = userRepository.findById(userId).orElseThrow(() -> new RuntimeException("User not found"));
        Group group = groupRepository.findById(groupId).orElseThrow(() -> new RuntimeException("Group not found"));
        user.getGroups().add(group);
        return ResponseEntity.ok(userRepository.save(user));
    }

    @PostMapping("/{userId}/roles/{roleId}")
    @Operation(summary = "Assign a role directly to a user")
    public ResponseEntity<User> assignRole(@PathVariable Long userId, @PathVariable Long roleId) {
        User user = userRepository.findById(userId).orElseThrow(() -> new RuntimeException("User not found"));
        Role role = roleRepository.findById(roleId).orElseThrow(() -> new RuntimeException("Role not found"));
        user.getRoles().add(role);
        return ResponseEntity.ok(userRepository.save(user));
    }

    @PostMapping("/invite")
    @Operation(summary = "Invite a new user via email")
    public ResponseEntity<String> inviteUser(@RequestBody CreateUserRequest request) {
        if (userRepository.findByUsername(request.getEmail()).isPresent()) {
            throw new UserAlreadyExistsException("User with this email already exists");
        }

        String token = UUID.randomUUID().toString();

        com.athena.userservice.model.Invitation invitation = com.athena.userservice.model.Invitation.builder()
                .token(token)
                .email(request.getEmail())
                .roles(request.getRoles() != null
                        ? request.getRoles().stream()
                                .map(name -> roleRepository.findByName(name)
                                        .orElseThrow(() -> new RuntimeException("Role not found: " + name)))
                                .collect(Collectors.toSet())
                        : new HashSet<>())
                .groups(request.getGroups() != null
                        ? request.getGroups().stream()
                                .map(name -> groupRepository.findByName(name)
                                        .orElseThrow(() -> new RuntimeException("Group not found: " + name)))
                                .collect(Collectors.toSet())
                        : new HashSet<>())
                .expiryDate(LocalDateTime.now().plusHours(24))
                .used(false)
                .build();

        invitationRepository.save(invitation);

        // Publish invitation event to notification-service via Athena exchange
        Map<String, Object> event = new HashMap<>();
        event.put("type", "USER_INVITATION");
        event.put("email", request.getEmail());
        event.put("token", token);
        rabbitTemplate.convertAndSend(
                AthenaRabbitMQConfig.SCORING_EXCHANGE,
                AthenaRabbitMQConfig.NOTIFICATION_KEY,
                event);

        return ResponseEntity.ok("Invitation sent to " + request.getEmail());
    }
}
