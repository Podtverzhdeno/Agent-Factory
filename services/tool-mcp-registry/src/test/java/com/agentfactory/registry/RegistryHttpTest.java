package com.agentfactory.registry;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

@SpringBootTest
@AutoConfigureMockMvc
class RegistryHttpTest {
    @Autowired MockMvc mvc;
    @Test void withoutIssuerAndJwksEveryRouteIsClosed() throws Exception {
        int status = mvc.perform(post("/v0/registry/select").contentType(MediaType.APPLICATION_JSON)
            .content("{\"required_capabilities\":[\"read_xlsx\"],\"allowed_effects\":[\"READ\"],\"max_risk\":\"LOW\",\"pinned_versions\":{},\"expected_schemas\":{}}"))
            .andReturn().getResponse().getStatus();
        assertThat(status).isIn(401, 403);
        int listStatus = mvc.perform(get("/v0/registry/manifests")).andReturn().getResponse().getStatus();
        assertThat(listStatus).isIn(401,403);
    }
}
