package com.agentfactory.api;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import javax.sql.DataSource;
import java.util.logging.Logger;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ScriptUtils;

/**
 * Opt-in, smoke-only bootstrap for Control Plane-owned proof-of-concept schema.
 * Never touches other services' public tables. No migrations are run in the
 * release profile without a separately approved production migration plan.
 *
 * Uses a single PostgreSQL transaction and an advisory lock to serialize
 * concurrent boots. The connection's normal JDBC currentSchema must be set
 * to this schema; the bootstrap fixes its own transaction search path.
 */
@Configuration(proxyBeanMethods = false)
@Profile("jdbc-poc & railway-smoke")
@ConditionalOnProperty(prefix = "factory.persistence", name = "bootstrap-poc-schema", havingValue = "true")
public class JdbcPocSchemaBootstrap {
    static final String SCHEMA = "cp_factory_poc";
    private static final Logger LOGGER = Logger.getLogger(JdbcPocSchemaBootstrap.class.getName());
    static final String V1 = "db/migration/V1__control_plane_poc.sql";
    static final String V2 = "db/migration/V2__tenant_event_inbox.sql";

    @Bean
    ApplicationRunner bootstrapPocSchema(DataSource source) {
        return args -> bootstrap(source);
    }

    static void bootstrap(DataSource source) {
        try(Connection c=source.getConnection()) {
            if (c==null) throw new IllegalStateException("POC_DATABASE_UNAVAILABLE");
            c.setAutoCommit(false);
            try (Statement s=c.createStatement()) {
                // This lock is transaction-scoped; a failed startup releases it.
                s.execute("SELECT pg_advisory_xact_lock(7846221)");
                s.execute("CREATE SCHEMA IF NOT EXISTS "+SCHEMA);
                s.execute("SET LOCAL search_path TO "+SCHEMA);
                s.execute("CREATE TABLE IF NOT EXISTS cp_schema_migration "
                    + "(version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)");
                apply(c,s,1,V1);
                apply(c,s,2,V2);
                SchemaReadinessController.verifySchema(c);
                // A synthetic, tenant-free marker verifies durability across
                // *real service restarts*, never writes business workflow data.
                s.execute("CREATE TABLE IF NOT EXISTS cp_poc_restart_probe "
                    + "(probe_key TEXT PRIMARY KEY, boots BIGINT NOT NULL CHECK (boots >= 1))");
                long boots;
                try(var probe=c.prepareStatement(
                    "INSERT INTO cp_poc_restart_probe(probe_key,boots) VALUES ('schema-liveness',1) "
                    + "ON CONFLICT(probe_key) DO UPDATE "
                    + "SET boots=cp_poc_restart_probe.boots+1 RETURNING boots")) {
                    try(var result=probe.executeQuery()) {
                        if(!result.next()) throw new IllegalStateException("POC_DURABILITY_PROBE_FAILED");
                        boots=result.getLong(1);
                    }
                }
                c.commit();
                LOGGER.info("event=control_plane.persistence outcome=SCHEMA_VERIFIED"
                    +" schema=cp_factory_poc migrations=2 boot_sequence="+boots);
            } catch (Exception failed) {
                try { c.rollback(); } catch(SQLException ignored) { }
                throw new IllegalStateException("POC_SCHEMA_BOOTSTRAP_FAILED");
            }
        } catch(SQLException failed) {
            // Do not leak driver-provided credentials, hostnames or query bodies.
            throw new IllegalStateException("POC_DATABASE_UNAVAILABLE");
        }
    }

    private static void apply(Connection c,Statement s,int version,String path) throws SQLException {
        boolean alreadyApplied;
        try (var check=c.prepareStatement(
                "SELECT 1 FROM cp_schema_migration WHERE version=?")) {
            check.setInt(1,version);
            try(ResultSet result=check.executeQuery()) { alreadyApplied=result.next(); }
        }
        if(!alreadyApplied) {
            ScriptUtils.executeSqlScript(c,new ClassPathResource(path));
            try(var put=c.prepareStatement(
                    "INSERT INTO cp_schema_migration(version) VALUES (?)")) {
                put.setInt(1,version);
                put.executeUpdate();
            }
        }
    }
}
