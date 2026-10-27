package com.agentfactory.api;

import com.agentfactory.control.JdbcAgentStore;
import com.agentfactory.control.JdbcWorkflowLedger;
import com.agentfactory.control.OutboxDispatcher;
import com.agentfactory.control.Ports;
import com.agentfactory.store.AgentStore;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Fail-closed *local runtime readiness*; deliberately not production acceptance.
 *
 * Liveness (/healthz), database connectivity (/persistencez) and migration
 * presence (/schemaz) have narrower meanings. A side-effecting Control Plane
 * cannot be locally ready with volatile storage, an absent command relay,
 * or the deliberately unauthenticated/fail-closed smoke profile.
 *
 * HTTP 200 means only that local components and database schema are available;
 * it does NOT attest real remote endpoints, service identity, holdout evidence
 * or ADR approval. Never publish JDBC URLs, errors, tokens or bean identities.
 */
@RestController
public final class RuntimeReadinessController {
    private static final Map<String,String> UNAVAILABLE=Map.of("readiness","unavailable");
    private static final Map<String,String> LOCAL_READY=Map.of("readiness","local-checks-passed");

    private final ObjectProvider<DataSource> sources;
    private final Ports.WorkflowLedger ledger;
    private final AgentStore store;
    private final ObjectProvider<OutboxDispatcher> relays;
    private final Environment environment;

    public RuntimeReadinessController(ObjectProvider<DataSource> sources,
        Ports.WorkflowLedger ledger, AgentStore store,
        ObjectProvider<OutboxDispatcher> relays, Environment environment) {
        this.sources=sources;
        this.ledger=ledger;
        this.store=store;
        this.relays=relays;
        this.environment=environment;
    }

    @GetMapping("/readyz")
    public ResponseEntity<Map<String,String>> ready() {
        if (environment.acceptsProfiles(Profiles.of("railway-smoke"))
            || !(ledger instanceof JdbcWorkflowLedger)
            || !(store instanceof JdbcAgentStore)
            || relays.getIfAvailable()==null) {
            return ResponseEntity.status(503).body(UNAVAILABLE);
        }
        try {
            DataSource source=sources.getIfAvailable();
            if (source==null) return ResponseEntity.status(503).body(UNAVAILABLE);
            try (Connection connection=source.getConnection()) {
                if (connection==null || !connection.isValid(2))
                    return ResponseEntity.status(503).body(UNAVAILABLE);
                SchemaReadinessController.verifySchema(connection);
                return ResponseEntity.ok(LOCAL_READY);
            }
        } catch (SQLException | RuntimeException unavailable) {
            // Authentication details, database names and schema errors stay private.
            return ResponseEntity.status(503).body(UNAVAILABLE);
        }
    }
}
