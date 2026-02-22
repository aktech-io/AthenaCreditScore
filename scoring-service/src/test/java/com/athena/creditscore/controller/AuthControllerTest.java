package com.athena.creditscore.controller;

import com.athena.creditscore.config.JwtUtil;
import com.athena.creditscore.dto.AuthRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AuthController.class)
@DisplayName("AuthController Tests")
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean private AuthenticationManager authenticationManager;
    @MockBean private UserDetailsService userDetailsService;
    @MockBean private JwtUtil jwtUtil;

    // Required by SecurityConfig to load context without a DB
    @MockBean
    private com.athena.creditscore.config.JwtAuthenticationFilter jwtAuthenticationFilter;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("POST /api/auth/admin/login — valid credentials → 200 + token")
    void adminLoginSuccess() throws Exception {
        var request = AuthRequest.builder().username("admin").password("secret").build();

        when(authenticationManager.authenticate(any())).thenReturn(
                new UsernamePasswordAuthenticationToken("admin", null,
                        List.of(new SimpleGrantedAuthority("ROLE_ADMIN")))
        );
        when(userDetailsService.loadUserByUsername("admin")).thenReturn(
                User.builder().username("admin").password("hashed")
                        .authorities(List.of(new SimpleGrantedAuthority("ROLE_ADMIN"))).build()
        );
        when(jwtUtil.generateToken("admin", List.of("ROLE_ADMIN"), null)).thenReturn("mock-jwt-token");

        mockMvc.perform(post("/api/auth/admin/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("admin"))
                .andExpect(jsonPath("$.roles").isArray());
    }

    @Test
    @DisplayName("POST /api/auth/admin/login — bad credentials → 401")
    void adminLoginFailure() throws Exception {
        var request = AuthRequest.builder().username("admin").password("wrong").build();

        when(authenticationManager.authenticate(any()))
                .thenThrow(new BadCredentialsException("Bad credentials"));

        mockMvc.perform(post("/api/auth/admin/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("POST /api/auth/admin/login — missing username → 400 validation error")
    void adminLoginMissingUsername() throws Exception {
        var request = AuthRequest.builder().password("secret").build(); // no username

        mockMvc.perform(post("/api/auth/admin/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/auth/customer/request-otp — valid phone → 200")
    void requestOtpSuccess() throws Exception {
        mockMvc.perform(post("/api/auth/customer/request-otp")
                        .param("phone", "+254712345678"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("+254712345678")));
    }

    @Test
    @DisplayName("POST /api/auth/customer/verify-otp — correct OTP → 200 + token")
    void verifyOtpSuccess() throws Exception {
        when(jwtUtil.generateToken(eq("+254712345678"), anyList(), isNull()))
                .thenReturn("customer-jwt");

        mockMvc.perform(post("/api/auth/customer/verify-otp")
                        .param("phone", "+254712345678")
                        .param("otp", "123456"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").exists())
                .andExpect(jsonPath("$.roles[0]").value("CUSTOMER"));
    }

    @Test
    @DisplayName("POST /api/auth/customer/verify-otp — wrong OTP → 401")
    void verifyOtpWrongCode() throws Exception {
        mockMvc.perform(post("/api/auth/customer/verify-otp")
                        .param("phone", "+254712345678")
                        .param("otp", "999999"))
                .andExpect(status().isUnauthorized());
    }
}
