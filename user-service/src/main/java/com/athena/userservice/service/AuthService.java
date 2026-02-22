package com.athena.userservice.service;

import com.athena.userservice.config.JwtUtil;
import com.athena.userservice.dto.AuthRequest;
import com.athena.userservice.dto.AuthResponse;
import com.athena.userservice.model.User;
import com.athena.userservice.repository.RoleRepository;
import com.athena.userservice.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final PasswordPolicyService passwordPolicyService;

    public AuthResponse register(AuthRequest request) {
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            throw new RuntimeException("Username already exists");
        }
        passwordPolicyService.validatePassword(request.getPassword());

        var defaultRole = roleRepository.findByName("USER")
                .orElseThrow(() -> new RuntimeException("Default role USER not found"));

        User user = User.builder()
                .username(request.getUsername())
                .password(passwordEncoder.encode(request.getPassword()))
                .status("ACTIVE")
                .build();
        user.getRoles().add(defaultRole);
        userRepository.save(user);

        List<String> roles = user.getRoles().stream().map(r -> r.getName()).collect(Collectors.toList());
        String token = jwtUtil.generateToken(user.getUsername(), roles, null);

        return AuthResponse.builder()
                .token(token)
                .username(user.getUsername())
                .roles(roles)
                .build();
    }

    public AuthResponse authenticate(AuthRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new RuntimeException("Invalid credentials"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new RuntimeException("Invalid credentials");
        }

        List<String> roles = user.getRoles().stream().map(r -> r.getName()).collect(Collectors.toList());
        List<String> groups = user.getGroups().stream().map(g -> g.getName()).collect(Collectors.toList());
        String token = jwtUtil.generateToken(user.getUsername(), roles, null);

        return AuthResponse.builder()
                .token(token)
                .username(user.getUsername())
                .firstName(user.getFirstName())
                .lastName(user.getLastName())
                .email(user.getEmail())
                .roles(roles)
                .groups(groups)
                .build();
    }
}
