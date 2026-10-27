package com.agentfactory.api;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Database connectivity probe, intentionally distinct from /healthz (process only).
 *
 * The smoke profile has no DataSource and returns HTTP 503, even when Tomcat is
 * healthy. HTTP 200 means only that the configured JDBC database is reachable;
 * it does NOT certify migrations, Agent Builder, Evaluation, JWTs or release safety.
 * Never reflect JDBC URLs, connection failures or credentials in this response.
 */
@RestController
public final class PersistenceProbeController {
    private static final Map<String, String> UNAVAILABLE = Map.of("persistence", "unavailable");
    private final ObjectProvider<DataSource> sources;

    public PersistenceProbeController(ObjectProvider<DataSource> sources) {
        this.sources = sources;
    }

    @GetMapping("/persistencez")
    public ResponseEntity<Map<String, String>> persistence() {
        DataSource source = sources.getIfAvailable();
        if (source == null) return ResponseEntity.status(503).body(UNAVAILABLE);
        try (Connection connection = source.getConnection()) {
            if (connection != null && connection.isValid(2))
                return ResponseEntity.ok(Map.of("persistence", "available"));
        } catch (SQLException | RuntimeException unavailable) {
            // Never disclose database topology or SQL failure details to clients.
        }
        return ResponseEntity.status(503).body(UNAVAILABLE);
    }
}
