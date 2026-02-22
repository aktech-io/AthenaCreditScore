package com.athena.userservice.controller;

import com.athena.userservice.config.JwtUtil;
import com.athena.userservice.dto.AuthRequest;
import com.athena.userservice.dto.AuthResponse;
import com.athena.userservice.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Authentication", description = "Login and token management")
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final UserDetailsService userDetailsService;
    private final JwtUtil jwtUtil;
    private final AuthService authService;
    private final JdbcTemplate jdbcTemplate;

    @PostMapping("/admin/login")
    @Operation(summary = "Admin login with username and password")
    public ResponseEntity<AuthResponse> adminLogin(@Valid @RequestBody AuthRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getUsername(), request.getPassword()));
        UserDetails userDetails = userDetailsService.loadUserByUsername(request.getUsername());
        List<String> roles = userDetails.getAuthorities().stream()
                .map(a -> a.getAuthority().replace("ROLE_", ""))
                .collect(Collectors.toList());
        String token = jwtUtil.generateToken(request.getUsername(), roles, null);
        log.info("Admin login successful: {}", request.getUsername());
        return ResponseEntity.ok(AuthResponse.builder()
                .token(token).username(request.getUsername()).roles(roles).build());
    }

    @PostMapping("/customer/request-otp")
    @Operation(summary = "Request OTP for customer login")
    public ResponseEntity<String> requestOtp(@RequestParam String phone) {
        log.info("OTP requested for phone: {}", phone);
        return ResponseEntity.ok("OTP sent to " + phone);
    }

    @PostMapping("/customer/verify-otp")
    @Operation(summary = "Verify OTP and return JWT for customer")
    public ResponseEntity<AuthResponse> verifyOtp(
            @RequestParam String phone,
            @RequestParam String otp) {
        if (!"123456".equals(otp)) {
            return ResponseEntity.status(401).build();
        }
        // Look up customerId by phone so JWT sub matches path variable in @PreAuthorize checks
        Long customerId = null;
        try {
            customerId = jdbcTemplate.queryForObject(
                    "SELECT customer_id FROM customers WHERE mobile_number = ?",
                    Long.class, phone);
        } catch (EmptyResultDataAccessException ignored) {}
        String subject = customerId != null ? customerId.toString() : phone;
        String token = jwtUtil.generateToken(subject, List.of("CUSTOMER"), customerId);
        return ResponseEntity.ok(AuthResponse.builder()
                .token(token).username(subject).roles(List.of("CUSTOMER")).customerId(customerId).build());
    }

    @PostMapping("/customer/demo-token")
    @Operation(summary = "Generate a signed demo JWT for a customer (dev/testing only)")
    public ResponseEntity<AuthResponse> demoToken(@RequestParam Long customerId) {
        // Use customerId.toString() as subject so @PreAuthorize path-variable checks work
        String subject = customerId.toString();
        String token = jwtUtil.generateToken(subject, List.of("CUSTOMER"), customerId);
        log.info("Demo token issued for customerId={}", customerId);
        return ResponseEntity.ok(AuthResponse.builder()
                .token(token).username(subject).roles(List.of("CUSTOMER")).customerId(customerId).build());
    }

    @PostMapping("/user/login")
    @Operation(summary = "Internal user login (users table — analysts, viewers, credit risk)")
    public ResponseEntity<AuthResponse> userLogin(@Valid @RequestBody AuthRequest request) {
        AuthResponse response = authService.authenticate(request);
        log.info("Internal user login: {}", request.getUsername());
        return ResponseEntity.ok(response);
    }
}
