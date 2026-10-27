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
        when(jwtDecoder.decode("starter-a"))
            .thenReturn(jwt("starter-a", "tenant-a", "factory:start"));
    }

    private static Jwt jwt(String token, String tenant, String scope) {
        Instant now = Instant.now();
        return Jwt.withTokenValue(token)
            .header("alg", "RS256")
            .subject("synthetic-test-service")
            .claim("tenant_id", tenant)
            .claim("scope", scope)
            .issuedAt(now)
            .expiresAt(now.plusSeconds(3_600))
            .build();
    }

    @Test
    void publicLivenessDoesNotRevealTenantData() throws Exception {
        http.perform(get("/healthz"))
            .andExpect(status().isOk());
    }

    @Test
    void processLivenessCannotMasqueradeAsDurablePersistence() throws Exception {
        http.perform(get("/healthz")).andExpect(status().isOk());
        http.perform(get("/persistencez")).andExpect(status().isServiceUnavailable())
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers
                .jsonPath("$.persistence").value("unavailable"));
    }

    @Test
    void schemaProbeRejectsSmokeWithoutDataSource() throws Exception {
        http.perform(get("/healthz")).andExpect(status().isOk());
        http.perform(get("/schemaz")).andExpect(status().isServiceUnavailable())
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers
                .jsonPath("$.schema").value("unavailable"));
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
    void malformedStartIsBadRequestNotInternalServerError() throws Exception {
        http.perform(post("/v1/workflows")
                .header("Authorization", "Bearer starter-a")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void workflowBodyCannotSelectAnotherTenant() throws Exception {
        http.perform(post("/v1/workflows")
                .header("Authorization", "Bearer starter-a")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"tenantId\":\"tenant-b\","
                    + "\"workflowId\":\"wf-forged\","
                    + "\"taskSnapshotId\":\"snap\","
                    + "\"correlationId\":\"c\","
                    + "\"idempotencyKey\":\"k\","
                    + "\"limits\":{\"maxRepairs\":2,\"maxUsd\":1,"
                    + "\"deadline\":\"2099-01-01T00:00:00Z\"}}"))
            .andExpect(status().isForbidden());
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
