package com.agentfactory.api;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.agentfactory.control.JdbcAgentStore;
import com.agentfactory.control.JdbcTransactionScope;
import com.agentfactory.control.JdbcWorkflowLedger;
import com.agentfactory.control.Ports;
import com.agentfactory.store.AgentStore;
import javax.sql.DataSource;
import java.sql.Connection;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Starts the real Spring application with JDBC opt-in (not just hand-built
 * adapters). Railway builds use an isolated localhost PostgreSQL 16; local
 * developers use a disposable Testcontainers instance. No skip fallback.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles({"jdbc-poc", "railway-smoke"})
final class JdbcSpringWiringIntegrationTest {
    private static final String LOCAL_URL = System.getenv("CONTROL_PLANE_TEST_JDBC_URL");
    private static final PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("control_plane_test")
            .withUsername("factory_test")
            .withPassword("synthetic_only");
    private static boolean startedContainer;

    static {
        if (LOCAL_URL != null && !LOCAL_URL.isBlank()) {
            if (!LOCAL_URL.matches("jdbc:postgresql://(127\\.0\\.0\\.1|localhost):[0-9]+/control_plane_test"))
                throw new IllegalStateException("UNSAFE_INTEGRATION_TEST_DATABASE_URL");
        } else {
            POSTGRES.start();
            startedContainer = true;
        }
    }

    @DynamicPropertySource
    static void database(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.jdbc-url", () ->
            startedContainer ? POSTGRES.getJdbcUrl() : LOCAL_URL);
        registry.add("spring.datasource.username", () ->
            startedContainer ? POSTGRES.getUsername() : "factory_test");
        registry.add("spring.datasource.password", () ->
            startedContainer ? POSTGRES.getPassword() : "synthetic_only");
    }

    @AfterAll
    static void closeDisposableDatabase() {
        if (startedContainer) POSTGRES.stop();
    }

    @Autowired private DataSource dataSource;
    @Autowired private Ports.WorkflowLedger workflowLedger;
    @Autowired private AgentStore agentStore;
    @Autowired private JdbcTransactionScope transactionScope;
    @Autowired private MockMvc http;

    @Test
    void springActuallyInjectsJdbcPersistenceWithLivePostgres() throws Exception {
        assertInstanceOf(JdbcWorkflowLedger.class, workflowLedger);
        assertInstanceOf(JdbcAgentStore.class, agentStore);
        assertNotNull(transactionScope);
        try (Connection connection = dataSource.getConnection()) {
            assertTrue(connection.isValid(3));
            assertTrue(connection.getMetaData().getURL().contains("control_plane_test"));
        }
    }

    @Test
    void jdbcProfileNeverOpensPrivateWorkflowApisToUnauthenticatedClients() throws Exception {
        http.perform(get("/healthz")).andExpect(status().isOk());
        http.perform(get("/v1/workflows/test").param("tenantId", "tenant-a"))
            .andExpect(status().isUnauthorized());
        http.perform(get("/v1/workflows/test").param("tenantId", "tenant-a")
                .header("Authorization", "Bearer synthetic-invalid-token"))
            .andExpect(status().isUnauthorized());
    }
}
