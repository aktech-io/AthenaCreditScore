package com.athena.creditscore.config;

import com.athena.creditscore.config.GlobalExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.BadCredentialsException;

import java.util.Map;

import static org.assertj.core.api.Assertions.*;

@DisplayName("GlobalExceptionHandler Tests")
class GlobalExceptionHandlerTest {

    private GlobalExceptionHandler handler;

    @BeforeEach
    void setUp() {
        handler = new GlobalExceptionHandler();
    }

    @Test
    @DisplayName("BadCredentialsException → 401 Unauthorized")
    void shouldReturn401ForBadCredentials() {
        ResponseEntity<Map<String, Object>> resp =
                handler.handleBadCredentials(new BadCredentialsException("bad"));

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
        assertThat(resp.getBody()).containsEntry("status", 401);
        assertThat(resp.getBody()).containsEntry("message", "Invalid credentials");
    }

    @Test
    @DisplayName("AccessDeniedException → 403 Forbidden")
    void shouldReturn403ForAccessDenied() {
        ResponseEntity<Map<String, Object>> resp =
                handler.handleAccessDenied(new AccessDeniedException("denied"));

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
        assertThat(resp.getBody()).containsEntry("status", 403);
    }

    @Test
    @DisplayName("IllegalArgumentException → 400 Bad Request with message")
    void shouldReturn400ForIllegalArgument() {
        ResponseEntity<Map<String, Object>> resp =
                handler.handleIllegal(new IllegalArgumentException("Invalid value"));

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(resp.getBody()).containsEntry("message", "Invalid value");
    }

    @Test
    @DisplayName("General Exception → 500 Internal Server Error")
    void shouldReturn500ForUnexpectedException() {
        ResponseEntity<Map<String, Object>> resp =
                handler.handleGeneral(new RuntimeException("Something went wrong"));

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(resp.getBody()).containsEntry("status", 500);
    }

    @Test
    @DisplayName("Error response body should always contain timestamp")
    void shouldIncludeTimestampInErrorBody() {
        ResponseEntity<Map<String, Object>> resp =
                handler.handleBadCredentials(new BadCredentialsException("x"));

        assertThat(resp.getBody()).containsKey("timestamp");
        assertThat(resp.getBody().get("timestamp")).isNotNull();
    }

    @Test
    @DisplayName("Error response body should always contain error field")
    void shouldIncludeErrorFieldInBody() {
        ResponseEntity<Map<String, Object>> resp =
                handler.handleAccessDenied(new AccessDeniedException("x"));

        assertThat(resp.getBody()).containsKey("error");
        assertThat(resp.getBody().get("error")).isEqualTo("Forbidden");
    }
}
