package com.athena.creditscore.config;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.io.Encoders;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.test.util.ReflectionTestUtils;

import java.security.Key;
import java.util.Collections;
import java.util.Date;
import java.util.List;

import static org.assertj.core.api.Assertions.*;

@DisplayName("JwtUtil Tests")
class JwtUtilTest {

    private JwtUtil jwtUtil;
    private String testSecret;

    @BeforeEach
    void setUp() {
        jwtUtil = new JwtUtil();
        // Generate a valid 256-bit base64 secret for tests
        Key key = Keys.secretKeyFor(SignatureAlgorithm.HS256);
        testSecret = Encoders.BASE64.encode(key.getEncoded());

        ReflectionTestUtils.setField(jwtUtil, "secret", testSecret);
        ReflectionTestUtils.setField(jwtUtil, "expiration", 86400000L); // 24h
    }

    private UserDetails testUser(String username) {
        return User.builder()
                .username(username)
                .password("password")
                .authorities(Collections.emptyList())
                .build();
    }

    @Nested
    @DisplayName("Token Generation")
    class GenerationTests {

        @Test
        @DisplayName("Should generate a non-null token")
        void shouldGenerateToken() {
            String token = jwtUtil.generateToken("admin", List.of("ADMIN"), null);
            assertThat(token).isNotNull().isNotBlank();
        }

        @Test
        @DisplayName("Should embed correct username as subject")
        void shouldEmbedUsername() {
            String token = jwtUtil.generateToken("analyst1", List.of("ANALYST"), null);
            assertThat(jwtUtil.extractUsername(token)).isEqualTo("analyst1");
        }

        @Test
        @DisplayName("Should embed roles as claims")
        void shouldEmbedRoles() {
            String token = jwtUtil.generateToken("admin", List.of("ADMIN", "ANALYST"), null);
            List<String> roles = jwtUtil.extractRoles(token);
            assertThat(roles).containsExactlyInAnyOrder("ADMIN", "ANALYST");
        }

        @Test
        @DisplayName("Should embed customerId when provided")
        void shouldEmbedCustomerId() {
            String token = jwtUtil.generateToken("customer", List.of("CUSTOMER"), 42L);
            assertThat(jwtUtil.extractCustomerId(token)).isEqualTo(42L);
        }

        @Test
        @DisplayName("Should return null customerId when not set")
        void shouldReturnNullCustomerIdIfAbsent() {
            String token = jwtUtil.generateToken("admin", List.of("ADMIN"), null);
            assertThat(jwtUtil.extractCustomerId(token)).isNull();
        }
    }

    @Nested
    @DisplayName("Token Validation")
    class ValidationTests {

        @Test
        @DisplayName("Valid token should pass isTokenValid")
        void shouldValidateCorrectToken() {
            String token = jwtUtil.generateToken("admin", List.of("ADMIN"), null);
            UserDetails userDetails = testUser("admin");
            assertThat(jwtUtil.isTokenValid(token, userDetails)).isTrue();
        }

        @Test
        @DisplayName("Token for different user should fail validation")
        void shouldFailForWrongUser() {
            String token = jwtUtil.generateToken("admin", List.of("ADMIN"), null);
            UserDetails otherUser = testUser("attacker");
            assertThat(jwtUtil.isTokenValid(token, otherUser)).isFalse();
        }

        @Test
        @DisplayName("Expired token should fail validation")
        void shouldFailForExpiredToken() {
            // Override expiration to immediate past
            ReflectionTestUtils.setField(jwtUtil, "expiration", -1000L);
            String token = jwtUtil.generateToken("admin", List.of("ADMIN"), null);
            UserDetails userDetails = testUser("admin");
            assertThat(jwtUtil.isTokenValid(token, userDetails)).isFalse();
        }

        @Test
        @DisplayName("Tampered token should throw exception on username extraction")
        void shouldRejectTamperedToken() {
            String token = jwtUtil.generateToken("admin", List.of("ADMIN"), null);
            String tampered = token.substring(0, token.length() - 10) + "TAMPERED##";
            assertThatThrownBy(() -> jwtUtil.extractUsername(tampered))
                    .isInstanceOf(Exception.class);
        }
    }
}
