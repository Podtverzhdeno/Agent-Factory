package com.agentfactory.api;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.List;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Read-only proof that the PostgreSQL storage schema required by Control Plane
 * V1/V2 exists and can be queried with this application's credentials.
 *
 * Unlike /healthz (process alive) and /persistencez (connection alive), this
 * detects missing schema objects and columns. It is NOT a data migration runner,
 * a writer health check, or a business release readiness check.
 */
@RestController
public final class SchemaReadinessController {
    private static final List<String> QUERIES = List.of(
        "SELECT tenant_id,workflow_id,idempotency_key,payload,action_pending,"
            + "notification_pending,terminal,revision FROM cp_workflow WHERE FALSE",
        "SELECT tenant_id,agent_id FROM cp_agent_lock WHERE FALSE",
        "SELECT tenant_id,agent_id,version,payload FROM cp_agent_version WHERE FALSE",
        "SELECT tenant_id,operation_kind,idempotency_key,fingerprint,result_json "
            + "FROM cp_agent_operation WHERE FALSE",
        "SELECT sequence_id,tenant_id,agent_id,payload FROM cp_agent_transition WHERE FALSE",
        "SELECT tenant_id,event_id,workflow_id,fingerprint FROM cp_event_inbox WHERE FALSE"
    );
    private static final Map<String,String> NOT_READY = Map.of("schema","unavailable");
    private final ObjectProvider<DataSource> sources;

    public SchemaReadinessController(ObjectProvider<DataSource> sources) {
        this.sources = sources;
    }

    @GetMapping("/schemaz")
    public ResponseEntity<Map<String,String>> schema() {
        try {
            DataSource source=sources.getIfAvailable();
            if(source==null) return ResponseEntity.status(503).body(NOT_READY);
            try(Connection connection=source.getConnection()) {
                if(connection==null || !connection.isValid(2))
                    return ResponseEntity.status(503).body(NOT_READY);
                verifySchema(connection);
                return ResponseEntity.ok(Map.of("schema","ready"));
            }
        } catch(SQLException | RuntimeException unavailable) {
            // Do not disclose hostnames, table names, SQL errors or credentials.
            return ResponseEntity.status(503).body(NOT_READY);
        }
    }

    /** Read-only fixed-shape queries. No data rows fetched or table writes made. */
    static void verifySchema(Connection connection) throws SQLException {
        try(Statement statement=connection.createStatement()) {
            statement.setQueryTimeout(2);
            for(String query:QUERIES) {
                try(ResultSet ignored=statement.executeQuery(query)) {
                    // WHERE FALSE makes missing tables/columns/SELECT grants visible
                    // without revealing tenant data or scanning application rows.
                }
            }
        }
    }
}
