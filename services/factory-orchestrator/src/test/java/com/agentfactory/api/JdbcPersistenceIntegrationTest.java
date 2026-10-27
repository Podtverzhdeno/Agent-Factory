package com.agentfactory.api;

import com.agentfactory.control.*;
import com.agentfactory.store.AgentStore;
import java.math.BigDecimal;
import java.sql.Connection;
import java.time.Instant;
import java.util.Map;
import java.util.Set;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.postgresql.ds.PGSimpleDataSource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Actual PostgreSQL tests in an isolated container; no running Builder/Evaluator required.
 * A Docker-capable CI host must run this class; skipped locally if Docker is unavailable.
 */
@Testcontainers(disabledWithoutDocker = true)
final class JdbcPersistenceIntegrationTest {
    @Container static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("control_plane_test").withUsername("factory_test").withPassword("synthetic_only");
    private static DataSource dataSource;
    private static final Instant NOW=Instant.parse("2026-10-27T09:00:00Z");
    private static final String TENANT="tenant-a";
    private static final String DIGEST="sha256:"+"a".repeat(64);
    private static final String TOOL="sha256:"+"b".repeat(64);
    private static final String MODEL="sha256:"+"c".repeat(64);

    @BeforeAll static void prepareSchema() throws Exception {
        PGSimpleDataSource ds=new PGSimpleDataSource();
        ds.setURL(PG.getJdbcUrl());ds.setUser(PG.getUsername());ds.setPassword(PG.getPassword());
        dataSource=ds;
        try(Connection c=dataSource.getConnection()) {
            ScriptUtils.executeSqlScript(c,new ClassPathResource("db/migration/V1__control_plane_poc.sql"));
        }
    }
    @BeforeEach void clearTables() throws Exception {
        try(Connection c=dataSource.getConnection();var s=c.createStatement()) {
            s.execute("TRUNCATE cp_workflow,cp_agent_transition,cp_agent_operation,cp_agent_version,cp_agent_lock RESTART IDENTITY CASCADE");
        }
    }
    private static JdbcTransactionScope tx() { return new JdbcTransactionScope(dataSource); }
    private static JacksonStateCodec codec() {
        return new JacksonStateCodec(new com.fasterxml.jackson.databind.ObjectMapper().findAndRegisterModules());
    }
    private static AgentStore.Evidence evidence() {
        return new AgentStore.Evidence("eval-01",DIGEST,"artifact://datasets/holdout-v1",DIGEST,
            "artifact://metrics/01","artifact://traces/01","artifact://holdout/independent",
            true,true,false,true,true,AgentStore.Risk.HIGH,Set.of());
    }
    private static AgentStore.Metadata metadata() {
        return new AgentStore.Metadata(TENANT,"agent-01","artifact://agent-spec/v1",DIGEST,
            Map.of("lookup.v1",TOOL),MODEL,"artifact://a2a/card-v1",evidence());
    }
    private static Protocol.Principal principal() {
        return new Protocol.Principal("human",TENANT,Set.of("factory:start","factory:read"));
    }
    private static Protocol.Start start() {
        return new Protocol.Start(TENANT,"wf-01","snapshot-01","start-key",
            new Protocol.Limits(2,new BigDecimal("3.00"),NOW.plusSeconds(3600)),"trace-01");
    }
    private ControlPlane orchestrator(JdbcWorkflowLedger ledger,AgentStore store) {
        return new ControlPlane(ledger,(tenant,snapshot) ->
            new Protocol.Snapshot(tenant,snapshot,"READY",DIGEST,
                "artifact://policies/v1","artifact://datasets/holdout-v1","owner","rev-1"),
            (actor,tenant,scope)-> {
                if(!tenant.equals(actor.tenantId()) || !actor.scopes().contains(scope))
                    throw new IllegalStateException("UNAUTHORIZED_TENANT_OR_SCOPE");
            },
            (tenant,w,purpose)->false, view->false,()->NOW,store,
            (tenant,run,digest,e)-> {
                if(!tenant.equals(TENANT) || !digest.equals(e.specDigest()))
                    throw new IllegalStateException("ATTESTATION_INVALID");
            });
    }

    @Test void workflowAndInboxOutboxSurviveFreshAdapterInstance() {
        var scope=tx();var store=new JdbcAgentStore(scope,codec());
        var first=new JdbcWorkflowLedger(scope,codec());
        orchestrator(first,store).start(principal(),start());
        var restored=new JdbcWorkflowLedger(tx(),codec());
        var workflow=restored.get(TENANT,"wf-01");
        assertEquals(Workflow.State.BUILDING,workflow.view().state());
        assertEquals(1,restored.withUndeliveredActions().size());
        assertEquals(1,restored.withUndeliveredEvents().size());
        assertEquals("wf-01",restored.byIdempotency(TENANT,"start-key").orElseThrow().view().workflowId());
        assertTrue(restored.byIdempotency("another-tenant","start-key").isEmpty());
        var replay=orchestrator(restored,new JdbcAgentStore(tx(),codec())).start(principal(),start());
        assertEquals("wf-01",replay.workflowId());
        assertEquals(1,restored.withUndeliveredActions().size());
    }

    @Test void workflowAndCandidateMutationRollbackTogetherOnFailure() {
        var scope=tx();var ledger=new JdbcWorkflowLedger(scope,codec());
        var store=new JdbcAgentStore(scope,codec());
        orchestrator(ledger,store).start(principal(),start());
        assertThrows(IllegalStateException.class,()->ledger.transact(TENANT,"wf-01",w->{
            store.registerCandidate(metadata(),"candidate-01");
            throw new IllegalStateException("INJECTED_CRASH");
        }));
        assertEquals(Workflow.State.BUILDING,ledger.get(TENANT,"wf-01").view().state());
        assertEquals(0,store.versions(TENANT,"agent-01").size());
    }

    @Test void versionsAndReleaseRollbackPersistAcrossRestart() {
        var store=new JdbcAgentStore(tx(),codec());
        var candidate=store.registerCandidate(metadata(),"candidate-01");
        assertEquals(1,candidate.version());
        assertEquals(candidate,store.registerCandidate(metadata(),"candidate-01"));
        assertThrows(IllegalStateException.class,()->store.promote(TENANT,"agent-01",1,
            "auto-incorrect",Set.of("release:approve"),true));
        store.promote(TENANT,"agent-01",1,"human-approval",Set.of("release:approve"),false);
        var recovered=new JdbcAgentStore(tx(),codec());
        assertEquals(DIGEST,recovered.active(TENANT,"agent-01").orElseThrow().specDigest());
        recovered.rollback(TENANT,"agent-01",1,"rollback-1");
        var after=new JdbcAgentStore(tx(),codec());
        assertTrue(after.active(TENANT,"agent-01").isEmpty());
        assertEquals(AgentStore.Channel.ROLLED_BACK,after.versions(TENANT,"agent-01").getFirst().channel());
        assertEquals(3,after.history(TENANT,"agent-01").size());
        assertTrue(after.versions("tenant-b","agent-01").isEmpty());
    }

    @Test void mismatchedIdempotencyCannotOverwriteEvidence() {
        var store=new JdbcAgentStore(tx(),codec());
        store.registerCandidate(metadata(),"candidate-01");
        var changed=new AgentStore.Metadata(TENANT,"agent-01","artifact://agent-spec/v1",DIGEST,
            Map.of("lookup.v1","sha256:"+"f".repeat(64)),MODEL,"artifact://a2a/card-v1",evidence());
        var conflict=assertThrows(IllegalStateException.class,()->store.registerCandidate(changed,"candidate-01"));
        assertEquals("IDEMPOTENCY_CONFLICT",conflict.getMessage());
        assertEquals(1,new JdbcAgentStore(tx(),codec()).versions(TENANT,"agent-01").size());
    }
}
