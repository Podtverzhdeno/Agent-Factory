package com.agentfactory.api;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Synthetic JWT security smoke tests: no production issuer, keys or service calls.
 * Authorization must happen before resolving tenant-specific workflow state.
 */
@SpringBootTest
@AutoConfigureMockMvc
final class ControlPlaneSecurityTest {
    @Autowired private MockMvc http;
    @MockitoBean private JwtDecoder jwtDecoder;

    @BeforeEach
    void issueSyntheticTokens() {
        when(jwtDecoder.decode("reader-b"))
            .thenReturn(jwt("reader-b", "tenant-b", "factory:read"));
        when(jwtDecoder.decode("reader-a"))
            .thenReturn(jwt("reader-a", "tenant-a", "factory:read"));
        when(jwtDecoder.decode("wrong-producer"))
            .thenReturn(jwt("wrong-producer", "tenant-a", "factory:events:evaluation"));
    }

    private static Jwt jwt(String token, String tenant, String scope) {
        Instant now = Instant.parse("2026-10-27T00:00:00Z");
        return Jwt.withTokenValue(token)
            .header("alg", "RS256")
            .subject("synthetic-test-service")
            .claim("tenant_id", tenant)
            .claim("scope", scope)
            .issuedAt(now)
            .expiresAt(now.plusSeconds(60 * 60 * 24 * 365))
            .build();
    }

    @Test
    void noJwtCannotReadWorkflow() throws Exception {
        http.perform(get("/v1/workflows/w1").param("tenantId", "tenant-a"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void crossTenantRequestIsDeniedBeforeLookup() throws Exception {
        http.perform(get("/v1/workflows/w1")
                .param("tenantId", "tenant-a")
                .header("Authorization", "Bearer reader-b"))
            .andExpect(status().isForbidden());
    }

    @Test
    void sameTenantScopeCanReachLookupButNotFindNonexistentWorkflow() throws Exception {
        http.perform(get("/v1/workflows/missing")
                .param("tenantId", "tenant-a")
                .header("Authorization", "Bearer reader-a"))
            .andExpect(status().isNotFound());
    }

    @Test
    void evaluationPublisherCannotSendBuilderEvent() throws Exception {
        http.perform(post("/internal/events/build")
                .header("Authorization", "Bearer wrong-producer")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isForbidden());
    }
}
