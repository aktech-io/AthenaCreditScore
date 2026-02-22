package com.athena.customerservice.config;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.security.SignatureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ExpiredJwtException.class)
    public ResponseEntity<Map<String, String>> handleExpiredJwtException(ExpiredJwtException e) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Token expired", "message", "Your session has expired. Please log in again."));
    }

    @ExceptionHandler(MalformedJwtException.class)
    public ResponseEntity<Map<String, String>> handleMalformedJwtException(MalformedJwtException e) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Invalid token", "message", "The provided token is invalid."));
    }

    @ExceptionHandler(SignatureException.class)
    public ResponseEntity<Map<String, String>> handleSignatureException(SignatureException e) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Invalid token signature", "message", "The token signature verification failed."));
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<Map<String, String>> handleDataIntegrityViolationException(DataIntegrityViolationException e) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(Map.of("error", "Duplicate record", "message", "A customer with the same mobile number or national ID already exists."));
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, String>> handleRuntimeException(RuntimeException e) {
        String message = e.getMessage();

        if (message != null && message.contains("Maker-checker")) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "Maker-Checker Violation", "message", message));
        }

        if (message != null && message.contains("not found")) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("error", "Not Found", "message", message));
        }

        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(Map.of("error", "Business Error",
                        "message", message != null ? message : "An unexpected error occurred."));
    }
}
