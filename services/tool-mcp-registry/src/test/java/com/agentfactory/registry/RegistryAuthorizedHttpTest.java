package com.agentfactory.registry;

import tools.jackson.databind.json.JsonMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;
import java.util.Set;

import static com.agentfactory.registry.ToolRegistry.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** HTTP adapter tests use mock JWT authentication; decoder trust-chain needs separate OIDC integration tests. */
@SpringBootTest(properties={
    "registry.security.issuer-uri=https://auth.example.test/",
    "registry.security.jwk-set-uri=https://auth.example.test/.well-known/jwks.json",
    "registry.security.audience=agent-factory"
})
@AutoConfigureMockMvc
@Import(RegistryAuthorizedHttpTest.SyntheticRegistryConfiguration.class)
class RegistryAuthorizedHttpTest {
    @TestConfiguration(proxyBeanMethods = false)
    static class SyntheticRegistryConfiguration {
        @Bean @Primary ToolRegistry syntheticRegistryForHttpTests() {
            return new ToolRegistry(Map.of(
                "artifact://schemas/file-input", new Shape(Map.of("file", FieldSpec.scalar(FieldType.STRING)), Set.of("file"), false),
                "artifact://schemas/rows", new Shape(Map.of("rows", FieldSpec.array(FieldSpec.scalar(FieldType.STRING))), Set.of("rows"), false)
            ), Set.of("artifact://approved/endpoints/xlsx"), Set.of("trusted:synthetic-test"));
        }
    }
    @Autowired MockMvc mvc;
    @Autowired JsonMapper mapper;

    private static SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor caller(
            String subject, String tenant, String scopes) {
        return jwt().jwt(token -> token.subject(subject).claim("tenant_id", tenant).claim("scope", scopes));
    }

    @Test void testLifecycleTenantAuthAndRevocation() throws Exception {
        Manifest manifest = new Manifest("0.1", "http.test.read", "1.0.0", "execute", Transport.MCP,
            Set.of("read_xlsx"), "artifact://schemas/file-input", "artifact://schemas/rows",
            Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW, Set.of("tenant-a"),
            "artifact://approved/endpoints/xlsx", Health.HEALTHY, "trusted:synthetic-test",
            "Read synthetic workbook", "").withComputedDigest();
        String body = mapper.writeValueAsString(manifest);

        mvc.perform(post("/v0/registry/manifests").with(caller("author", "tenant-a", "registry:register"))
            .contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("DRAFT"));
        mvc.perform(post("/v0/registry/manifests/http.test.read/1.0.0/execute/approve")
            .with(caller("author", "tenant-a", "registry:approve")))
            .andExpect(status().isForbidden());
        mvc.perform(post("/v0/registry/manifests/http.test.read/1.0.0/execute/approve")
            .with(caller("reviewer", "tenant-a", "registry:approve")))
            .andExpect(status().isOk());

        String query = """
            {"required_capabilities":["read_xlsx"],"allowed_effects":["read"],
             "max_risk":"low","pinned_versions":{"http.test.read":"1.0.0"},"expected_schemas":{}}
            """;
        mvc.perform(post("/v0/registry/select").with(caller("builder", "tenant-a", "registry:lookup xlsx:read"))
            .contentType(MediaType.APPLICATION_JSON).content(query))
            .andExpect(status().isOk()).andExpect(jsonPath("$.decision").value("SELECTED"))
            .andExpect(jsonPath("$.selected_tools[0].tool_id").value("http.test.read"));
        mvc.perform(get("/v0/registry/manifests")
            .with(caller("builder", "tenant-a", "registry:lookup xlsx:read")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].risk_level").value("low"))
            .andExpect(jsonPath("$[0].side_effects[0]").value("read"));
        mvc.perform(get("/v0/registry/builder/manifests")
            .with(caller("builder", "tenant-a", "registry:lookup xlsx:read")))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].approved").value(true))
            .andExpect(jsonPath("$[0].risk_level").value("low"))
            .andExpect(jsonPath("$[0].tool_id").value("http.test.read"));
        mvc.perform(get("/v0/registry/builder/manifests")
            .with(caller("builder", "tenant-b", "registry:lookup xlsx:read")))
            .andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(0));
        mvc.perform(post("/v0/registry/select").with(caller("builder", "tenant-b", "registry:lookup xlsx:read"))
            .contentType(MediaType.APPLICATION_JSON).content(query))
            .andExpect(status().isOk()).andExpect(jsonPath("$.decision").value("BLOCKED"))
            .andExpect(jsonPath("$.denials[0].tool_id").value(""));
        mvc.perform(post("/v0/registry/select").with(caller("builder", "tenant-a", "registry:lookup"))
            .contentType(MediaType.APPLICATION_JSON).content(query))
            .andExpect(status().isOk()).andExpect(jsonPath("$.denials[0].code").value("MISSING_PERMISSION"));

        mvc.perform(get("/v0/registry/audit").with(caller("auditor", "tenant-a", "registry:audit")))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].action").value("REGISTERED"));
        mvc.perform(get("/v0/registry/audit").with(caller("builder", "tenant-a", "registry:lookup")))
            .andExpect(status().isForbidden());
        mvc.perform(post("/v0/registry/manifests/http.test.read/1.0.0/execute/revoke")
            .with(caller("reviewer", "tenant-a", "registry:approve")))
            .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REVOKED"));
        mvc.perform(post("/v0/registry/select").with(caller("builder", "tenant-a", "registry:lookup xlsx:read"))
            .contentType(MediaType.APPLICATION_JSON).content(query))
            .andExpect(status().isOk()).andExpect(jsonPath("$.decision").value("BLOCKED"));
    }
    @Test void testWireEnumsMatchFrozenV0Contract() throws Exception {
        String request = """
            {"required_capabilities":["read_xlsx"],"allowed_effects":["read"],
             "max_risk":"low","pinned_versions":{},"expected_schemas":{}}
            """;
        SelectionRequest parsed = mapper.readValue(request, SelectionRequest.class);
        org.assertj.core.api.Assertions.assertThat(parsed.maxRisk()).isEqualTo(Risk.LOW);
        org.assertj.core.api.Assertions.assertThat(parsed.allowedEffects()).containsExactly(Effect.READ);
        String json = mapper.writeValueAsString(parsed);
        org.assertj.core.api.Assertions.assertThat(json).contains("\"max_risk\":\"low\"")
            .contains("\"allowed_effects\":[\"read\"]");
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> mapper.readValue(
            request.replace("\"low\"", "\"LOW\""), SelectionRequest.class))
            .isInstanceOf(RuntimeException.class);
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> mapper.readValue(
            request.replace("\"read\"", "\"unknown_effect\""), SelectionRequest.class))
            .isInstanceOf(RuntimeException.class);
    }

    @Test void testRegistrationCannotCrossTenantOrAcceptUnknownFields() throws Exception {
        Manifest other = new Manifest("0.1", "http.multi.tenant", "1.0.0", "execute", Transport.MCP,
            Set.of("read_xlsx"), "artifact://schemas/file-input", "artifact://schemas/rows",
            Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW, Set.of("tenant-a", "tenant-b"),
            "artifact://approved/endpoints/xlsx", Health.HEALTHY, "trusted:synthetic-test",
            "Untrusted multi tenant", "").withComputedDigest();
        mvc.perform(post("/v0/registry/manifests").with(caller("author", "tenant-a", "registry:register"))
            .contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsString(other)))
            .andExpect(status().isForbidden());
        mvc.perform(post("/v0/registry/select").with(caller("builder", "tenant-a", "registry:lookup"))
            .contentType(MediaType.APPLICATION_JSON).content("""
                {"required_capabilities":["read_xlsx"],"allowed_effects":["read"],
                 "max_risk":"low","pinned_versions":{},"expected_schemas":{},"unexpected_grants":["admin:root"]}
                """))
            .andExpect(status().isBadRequest());
    }
}
