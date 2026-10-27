package com.agentfactory.api;

import com.agentfactory.control.*;
import com.agentfactory.store.AgentStore;
import java.math.BigDecimal;
import java.sql.Connection;
import java.time.Instant;
import java.util.Map;
import java.util.Set;
import javax.sql.DataSource;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.postgresql.ds.PGSimpleDataSource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.testcontainers.containers.PostgreSQLContainer;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Actual PostgreSQL integration tests, never skipped when Docker is unavailable.
 * Uses Testcontainers locally, or a *localhost-only, disposable* PostgreSQL
 * during the Railway Docker image build. No production database is permitted.
 */
final class JdbcPersistenceIntegrationTest {
    private static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("control_plane_test").withUsername("factory_test").withPassword("synthetic_only");
    private static boolean dockerPostgresStarted;
    private static DataSource dataSource;
    private static final Instant NOW=Instant.parse("2026-10-27T09:00:00Z");
    private static final String TENANT="tenant-a";
    private static final String DIGEST="sha256:"+"a".repeat(64);
    private static final String TOOL="sha256:"+"b".repeat(64);
    private static final String MODEL="sha256:"+"c".repeat(64);

    @BeforeAll static void prepareSchema() throws Exception {
        String localJdbc=System.getenv("CONTROL_PLANE_TEST_JDBC_URL");
        PGSimpleDataSource ds=new PGSimpleDataSource();
        if(localJdbc==null || localJdbc.isBlank()) {
            PG.start();
            dockerPostgresStarted=true;
            ds.setURL(PG.getJdbcUrl());
            ds.setUser(PG.getUsername());
            ds.setPassword(PG.getPassword());
        } else {
            // This test TRUNCATES tables. Never run it against a remote/prod DB.
            if(!localJdbc.matches("jdbc:postgresql://(127\\.0\\.0\\.1|localhost):[0-9]+/control_plane_test")) {
                throw new IllegalStateException("UNSAFE_INTEGRATION_TEST_DATABASE_URL");
            }
            ds.setURL(localJdbc);
            ds.setUser("factory_test");
            ds.setPassword("synthetic_only");
        }
        dataSource=ds;
        try(Connection c=dataSource.getConnection()) {
            ScriptUtils.executeSqlScript(c,new ClassPathResource("db/migration/V1__control_plane_poc.sql"));
            ScriptUtils.executeSqlScript(c,new ClassPathResource("db/migration/V2__tenant_event_inbox.sql"));
        }
    }

    @AfterAll static void stopContainerIfStarted() {
        if(dockerPostgresStarted) PG.stop();
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
    private static AgentStore.Evidence forRun(AgentStore.Evidence source,String runId) {
        return new AgentStore.Evidence(runId,source.specDigest(),source.datasetRef(),
            source.baselineDigest(),source.metricsRef(),source.traceRef(),
            source.holdoutEvidenceRef(),source.independent(),source.passed(),
            source.safetyVeto(),source.effectsVerified(),source.nonRegression(),
            source.risk(),source.approvals());
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
        return orchestrator(ledger,store,false);
    }

    private ControlPlane orchestrator(JdbcWorkflowLedger ledger,AgentStore store,boolean automaticRelease) {
        return new ControlPlane(ledger,(tenant,snapshot) ->
            new Protocol.Snapshot(tenant,snapshot,"READY",DIGEST,
                "artifact://policies/v1","artifact://datasets/holdout-v1","owner","rev-1"),
            (actor,tenant,scope)-> {
                if(!tenant.equals(actor.tenantId()) || !actor.scopes().contains(scope))
                    throw new IllegalStateException("UNAUTHORIZED_TENANT_OR_SCOPE");
            },
            (tenant,w,purpose)->false, view->automaticRelease,()->NOW,store,
            (tenant,run,digest,e)-> {
                if(!tenant.equals(TENANT) || !digest.equals(e.specDigest()))
                    throw new IllegalStateException("ATTESTATION_INVALID");
            });
    }

    @Test void foreignAttestedEvaluationRunCannotCreateDurableCandidate() {
        var scope=tx();
        var ledger=new JdbcWorkflowLedger(scope,codec());
        var store=new JdbcAgentStore(scope,codec());
        var plane=orchestrator(ledger,store,true);
        plane.start(principal(),start());

        var relay=new OutboxDispatcher(ledger,
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> {throw new AssertionError("Unexpected GEPARD");},
            command -> {throw new AssertionError("Unexpected Soup");});
        assertEquals(1,relay.dispatchPending());
        plane.onBuild(new Protocol.Principal("builder",TENANT,Set.of("factory:events:build")),
            new Protocol.BuildFinished(
                new Protocol.Header("0.1","foreign-test-build",TENANT,"wf-01",
                    ledger.get(TENANT,"wf-01").view().pendingOperationId(),"trace-01",NOW),
                true,"agent-01","artifact://agent-spec/v1",DIGEST,
                Map.of("lookup.v1",TOOL),MODEL,"artifact://a2a/card-v1",null,false));
        assertEquals(1,relay.dispatchPending());

        String actualRun=ledger.get(TENANT,"wf-01").view().pendingOperationId();
        assertNotEquals("foreign-evaluation-run",actualRun);
        var event=new Protocol.EvaluationFinished(new Protocol.Header(
                "0.1","foreign-test-evaluation",TENANT,"wf-01",
                actualRun,"trace-01",NOW),
            "foreign-evaluation-run",DIGEST,forRun(evidence(),"foreign-evaluation-run"),
            new BigDecimal("0.1"),null,false);
        var result=plane.onEvaluation(new Protocol.Principal("evaluator",TENANT,
            Set.of("factory:events:evaluation")),event);
        assertEquals(Workflow.State.BLOCKED,result.state());
        assertEquals("EVALUATION_RUN_MISMATCH",result.errorCode());

        var restartedLedger=new JdbcWorkflowLedger(tx(),codec());
        var restartedStore=new JdbcAgentStore(tx(),codec());
        assertEquals(Workflow.State.BLOCKED,restartedLedger.get(TENANT,"wf-01").view().state());
        assertEquals("EVALUATION_RUN_MISMATCH",
            restartedLedger.get(TENANT,"wf-01").view().errorCode());
        assertTrue(restartedStore.versions(TENANT,"agent-01").isEmpty());
        assertEquals(0,new OutboxDispatcher(restartedLedger,
            command -> {throw new AssertionError("Stale build replay");},
            command -> {throw new AssertionError("Stale evaluation replay");},
            command -> {throw new AssertionError("Stale optimizer replay");},
            command -> {throw new AssertionError("Stale Soup replay");}).dispatchPending());
    }

    @Test void schemaProbeReportsReadyAfterBothRealPostgresMigrations() {
        // prepareSchema() applied V1+V2 in the disposable test DB. Prove
        // that the same controller which refuses unconfigured installations
        // acknowledges the complete migrated schema with no table writes.
        var factory=new org.springframework.beans.factory.support.StaticListableBeanFactory();
        factory.addBean("migratedTestDatabase",dataSource);
        var result=new SchemaReadinessController(
            factory.getBeanProvider(javax.sql.DataSource.class)).schema();
        assertEquals(org.springframework.http.HttpStatus.OK,result.getStatusCode());
        assertEquals("ready",result.getBody().get("schema"));
        assertEquals(1,result.getBody().size());
    }

    @Test void schemaProbeRejectsMissingV2WithinRollbackOnlyDisposableSchema() throws Exception {
        // Run the V1-only negative test in a rolled-back transaction on the
        // already disposable localhost test DB. No live Railway DB is touched.
        try(Connection connection=dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                try(var create=connection.createStatement()) {
                    create.execute("CREATE SCHEMA cp_probe_incomplete");
                }
                connection.setSchema("cp_probe_incomplete");
                ScriptUtils.executeSqlScript(connection,
                    new ClassPathResource("db/migration/V1__control_plane_poc.sql"));
                var prior=connection.setSavepoint();
                assertThrows(java.sql.SQLException.class,
                    () -> SchemaReadinessController.verifySchema(connection));
                // Missing table raises a PostgreSQL transaction error: clear
                // its abort state before applying the forward-only V2 script.
                connection.rollback(prior);
                ScriptUtils.executeSqlScript(connection,
                    new ClassPathResource("db/migration/V2__tenant_event_inbox.sql"));
                assertDoesNotThrow(() -> SchemaReadinessController.verifySchema(connection));
            } finally {
                // Roll back schema creation itself, not merely its contents.
                connection.rollback();
            }
        }
    }

    @Test void verifiedLowRiskEvaluationAndAutoReleaseShareSingleCommit() {
        var tx=tx();
        var ledger=new JdbcWorkflowLedger(tx,codec());
        var store=new JdbcAgentStore(tx,codec());
        var control=orchestrator(ledger,store,true);
        control.start(principal(),start());

        var relay=new OutboxDispatcher(ledger,
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> { throw new AssertionError("Unexpected GEPARD"); },
            command -> { throw new AssertionError("Unexpected Soup"); });
        assertEquals(1,relay.dispatchPending());

        var buildPrincipal=new Protocol.Principal("builder",TENANT,Set.of("factory:events:build"));
        var buildHeader=new Protocol.Header("0.1","build-done",TENANT,"wf-01",
            ledger.get(TENANT,"wf-01").view().pendingOperationId(),"trace-01",NOW);
        control.onBuild(buildPrincipal,new Protocol.BuildFinished(buildHeader,true,"agent-01",
            "artifact://agent-spec/v1",DIGEST,Map.of("lookup",TOOL),MODEL,
            "artifact://a2a/card-v1",null,false));
        assertEquals(1,relay.dispatchPending());

        var evaluationPrincipal=new Protocol.Principal("evaluator",TENANT,Set.of("factory:events:evaluation"));
        var before=ledger.get(TENANT,"wf-01").view().revision();
        var evaluationHeader=new Protocol.Header("0.1","evaluation-pass",TENANT,"wf-01",
            ledger.get(TENANT,"wf-01").view().pendingOperationId(),"trace-01",NOW);
        var lowRisk=new AgentStore.Evidence(evaluationHeader.operationId(),DIGEST,"artifact://datasets/holdout-v1",
            DIGEST,"artifact://metrics/01","artifact://traces/01","artifact://holdout/independent",
            true,true,false,true,true,AgentStore.Risk.LOW,Set.of());
        var released=control.onEvaluation(evaluationPrincipal,new Protocol.EvaluationFinished(
            evaluationHeader,evaluationHeader.operationId(),DIGEST,lowRisk,new BigDecimal("0.1"),null,false));

        assertEquals(Workflow.State.RELEASED,released.state());
        assertEquals(before+1,released.revision());
        assertEquals(released.revision(),new JdbcWorkflowLedger(tx(),codec())
            .get(TENANT,"wf-01").view().revision());
        assertEquals(DIGEST,new JdbcAgentStore(tx(),codec())
            .active(TENANT,"agent-01").orElseThrow().specDigest());
        var restarted=orchestrator(new JdbcWorkflowLedger(tx(),codec()),
            new JdbcAgentStore(tx(),codec()),true);
        var releaseActor=new Protocol.Principal("releaser",TENANT,Set.of("factory:release"));
        var duplicateWithDifferentKey=assertThrows(IllegalStateException.class,()->
            restarted.release(releaseActor,TENANT,"wf-01","unexpected-manual-key"));
        assertEquals("IDEMPOTENCY_CONFLICT",duplicateWithDifferentKey.getMessage());
    }

    @Test void injectedCrashInsideAutoReleaseRollsBackEntireEvaluationAndCanRetry() {
        var shared=tx();
        var ledger=new JdbcWorkflowLedger(shared,codec());
        var realStore=new JdbcAgentStore(shared,codec());
        AgentStore failingStore=(AgentStore)java.lang.reflect.Proxy.newProxyInstance(
            AgentStore.class.getClassLoader(),new Class<?>[]{AgentStore.class},
            (proxy,method,args)->{
                try {
                    Object result=method.invoke(realStore,args);
                    if("promote".equals(method.getName()))
                        throw new IllegalStateException("INJECTED_AFTER_PROMOTION");
                    return result;
                } catch(java.lang.reflect.InvocationTargetException wrapped) {
                    throw wrapped.getCause();
                }
            });
        var control=orchestrator(ledger,failingStore,true);
        control.start(principal(),start());
        var relay=new OutboxDispatcher(ledger,
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> {throw new AssertionError("Unexpected optimization");},
            command -> {throw new AssertionError("Unexpected training");});
        assertEquals(1,relay.dispatchPending());
        var builder=new Protocol.Principal("builder",TENANT,Set.of("factory:events:build"));
        control.onBuild(builder,new Protocol.BuildFinished(
            new Protocol.Header("0.1","build-complete",TENANT,"wf-01",
                ledger.get(TENANT,"wf-01").view().pendingOperationId(),"trace-01",NOW),
            true,"agent-01","artifact://agent-spec/v1",DIGEST,Map.of("lookup",TOOL),
            MODEL,"artifact://a2a/card-v1",null,false));
        assertEquals(1,relay.dispatchPending());

        var evaluator=new Protocol.Principal("evaluator",TENANT,Set.of("factory:events:evaluation"));
        String evaluationOperation=ledger.get(TENANT,"wf-01").view().pendingOperationId();
        var holdout=new AgentStore.Evidence(evaluationOperation,DIGEST,"artifact://datasets/holdout-v1",
            DIGEST,"artifact://metrics/01","artifact://traces/01","artifact://holdout/01",
            true,true,false,true,true,AgentStore.Risk.LOW,Set.of());
        var outcome=new Protocol.EvaluationFinished(new Protocol.Header(
            "0.1","evaluation-complete",TENANT,"wf-01",
            evaluationOperation,"trace-01",NOW),
            evaluationOperation,DIGEST,holdout,new BigDecimal("0.1"),null,false);
        assertEquals("INJECTED_AFTER_PROMOTION",
            assertThrows(IllegalStateException.class,()->
                control.onEvaluation(evaluator,outcome)).getMessage());
        assertEquals(Workflow.State.TESTING,new JdbcWorkflowLedger(tx(),codec())
            .get(TENANT,"wf-01").view().state());
        assertTrue(new JdbcAgentStore(tx(),codec()).versions(TENANT,"agent-01").isEmpty());

        var recoveredScope=tx();
        var recovered=orchestrator(new JdbcWorkflowLedger(recoveredScope,codec()),
            new JdbcAgentStore(recoveredScope,codec()),true);
        assertEquals(Workflow.State.RELEASED,recovered.onEvaluation(evaluator,outcome).state());
        assertTrue(new JdbcAgentStore(tx(),codec()).active(TENANT,"agent-01").isPresent());
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

    @Test void pendingCommandStateSurvivesDispatchAndRestart() {
        var first=new JdbcWorkflowLedger(tx(),codec());
        orchestrator(first,new JdbcAgentStore(tx(),codec())).start(principal(),start());
        var restored=new JdbcWorkflowLedger(tx(),codec());
        var deliveries=new java.util.concurrent.atomic.AtomicInteger();
        var relay=new OutboxDispatcher(restored,
            c -> { deliveries.incrementAndGet(); return new Protocol.CommandReceipt(c.operationId(),true); },
            c -> { throw new AssertionError("Unexpected Evaluation"); },
            c -> { throw new AssertionError("Unexpected GEPARD"); },
            c -> { throw new AssertionError("Unexpected Soup"); });
        assertEquals(1,relay.dispatchPending());
        assertEquals(1,deliveries.get());
        assertTrue(new JdbcWorkflowLedger(tx(),codec()).withUndeliveredActions().isEmpty());
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

    @Test void caughtNestedSqlFailureCannotCommitAgentVersion() {
        var scope=tx();
        var store=new JdbcAgentStore(scope,codec());
        var result=assertThrows(IllegalStateException.class,()->scope.transaction(c -> {
            try {
                scope.transaction(nested -> {
                    assertSame(c,nested);
                    store.registerCandidate(metadata(),"candidate-nested-failure");
                    throw new java.sql.SQLException("injected failure after candidate registration");
                });
            } catch (JdbcTransactionScope.PersistenceFailure expected) {
                // Test rollback-only propagation through a caught nested exception.
            }
            return null;
        }));
        assertEquals("TRANSACTION_MARKED_ROLLBACK_ONLY",result.getMessage());
        assertTrue(new JdbcAgentStore(tx(),codec()).versions(TENANT,"agent-01").isEmpty());
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

    @Test void mismatchedStoredWorkflowTenantFailsClosed() throws Exception {
        var ledger=new JdbcWorkflowLedger(tx(),codec());
        orchestrator(ledger,new JdbcAgentStore(tx(),codec())).start(principal(),start());
        try(Connection c=dataSource.getConnection();var statement=c.prepareStatement(
            "UPDATE cp_workflow SET tenant_id=? WHERE tenant_id=? AND workflow_id=?")) {
            statement.setString(1,"tenant-b");statement.setString(2,TENANT);
            statement.setString(3,"wf-01");
            assertEquals(1,statement.executeUpdate());
        }
        var error=assertThrows(IllegalStateException.class,()->
            ledger.get("tenant-b","wf-01"));
        assertEquals("STORED_WORKFLOW_IDENTITY_MISMATCH",error.getMessage());
    }

    @Test void mismatchedStoredAgentVersionTenantFailsClosed() throws Exception {
        var store=new JdbcAgentStore(tx(),codec());
        var valid=store.registerCandidate(metadata(),"candidate-01");
        var forged=new AgentStore.Version("tenant-b",valid.agentId(),valid.version(),
            valid.specRef(),valid.specDigest(),valid.toolDigests(),valid.modelRouteDigest(),
            valid.a2aCardRef(),valid.rollbackRef(),valid.evidence(),valid.channel());
        try(Connection c=dataSource.getConnection();var statement=c.prepareStatement(
            "UPDATE cp_agent_version SET payload=? WHERE tenant_id=? AND agent_id=? AND version=?")) {
            statement.setString(1,codec().write(forged));statement.setString(2,TENANT);
            statement.setString(3,"agent-01");statement.setLong(4,valid.version());
            assertEquals(1,statement.executeUpdate());
        }
        var error=assertThrows(IllegalStateException.class,()->
            store.versions(TENANT,"agent-01"));
        assertEquals("STORED_AGENT_VERSION_IDENTITY_MISMATCH",error.getMessage());
    }

    @Test void idempotentCandidateIgnoresMapInsertionOrderAcrossRestart() {
        var firstTools=new java.util.LinkedHashMap<String,String>();
        firstTools.put("lookup.v1",TOOL);
        firstTools.put("read.v1",DIGEST);
        var secondTools=new java.util.LinkedHashMap<String,String>();
        secondTools.put("read.v1",DIGEST);
        secondTools.put("lookup.v1",TOOL);
        AgentStore.Metadata a=new AgentStore.Metadata(TENANT,"agent-01",
            "artifact://agent-spec/v1",DIGEST,firstTools,MODEL,null,evidence());
        AgentStore.Metadata b=new AgentStore.Metadata(TENANT,"agent-01",
            "artifact://agent-spec/v1",DIGEST,secondTools,MODEL,null,evidence());
        var created=new JdbcAgentStore(tx(),codec()).registerCandidate(a,"stable-idem");
        var replay=new JdbcAgentStore(tx(),codec()).registerCandidate(b,"stable-idem");
        assertEquals(created.version(),replay.version());
        assertEquals(1,new JdbcAgentStore(tx(),codec()).versions(TENANT,"agent-01").size());
    }

    @Test void lateOutboxFailureCannotOverwritePersistedDeadlineReason() {
        var scope=tx();
        var ledger=new JdbcWorkflowLedger(scope,codec());
        var store=new JdbcAgentStore(scope,codec());
        orchestrator(ledger,store).start(principal(),start());
        // The fifth failure normally blocks with OUTBOX_DELIVERY_EXHAUSTED.
        // A deadline may terminate that workflow while the fifth HTTP call is in flight.
        var deadlineSweeper=new ControlPlane(ledger,
            (tenant,snapshot)->{ throw new IllegalStateException("NOT_USED"); },
            (actor,tenant,permission)->{throw new IllegalStateException("NOT_USED");},
            (tenant,id,permission)->false, view->false,
            ()->NOW.plusSeconds(4_000), store,
            (tenant,id,digest,evidence)->{throw new IllegalStateException("NOT_USED");});
        var calls=new java.util.concurrent.atomic.AtomicInteger();
        var relay=new OutboxDispatcher(ledger,
            command -> {
                if(calls.incrementAndGet()==5)
                    assertEquals(1,deadlineSweeper.expireDueWorkflows());
                throw new IllegalStateException("REMOTE_UNAVAILABLE");
            },
            command->{throw new AssertionError("Unexpected Evaluation");},
            command->{throw new AssertionError("Unexpected optimization");},
            command->{throw new AssertionError("Unexpected Soup");});
        for(int i=0;i<5;i++) assertEquals(0,relay.dispatchPending());
        assertEquals(5,calls.get());
        var recovered=new JdbcWorkflowLedger(tx(),codec());
        assertEquals(Workflow.State.BLOCKED,recovered.get(TENANT,"wf-01").view().state());
        assertEquals("TIME_BUDGET_EXHAUSTED",recovered.get(TENANT,"wf-01").view().errorCode());
        assertTrue(recovered.withUndeliveredActions().isEmpty());
    }

    @Test void consumedInboxEventSurvivesRestartAndRejectsConflictingReplay() throws Exception {
        var scope=tx();
        var ledger=new JdbcWorkflowLedger(scope,codec());
        var store=new JdbcAgentStore(scope,codec());
        var plane=orchestrator(ledger,store);
        plane.start(principal(),start());
        var dispatcher=new OutboxDispatcher(ledger,
            c -> new Protocol.CommandReceipt(c.operationId(),true),
            c -> new Protocol.CommandReceipt(c.operationId(),true),
            c -> new Protocol.CommandReceipt(c.operationId(),true),
            c -> new Protocol.CommandReceipt(c.operationId(),true));
        assertEquals(1,dispatcher.dispatchPending());
        var header=new Protocol.Header("0.1","durable-build-event",TENANT,"wf-01",
            plane.get(principal(),TENANT,"wf-01").pendingOperationId(),"trace-01",NOW);
        var original=new Protocol.BuildFinished(header,true,"agent-01",
            "artifact://agent-spec/a1",DIGEST,Map.of("lookup",TOOL),
            MODEL,"artifact://a2a/card",null,false);
        var builder=new Protocol.Principal("builder",TENANT,Set.of("factory:events:build"));
        assertEquals(Workflow.State.TESTING,plane.onBuild(builder,original).state());

        // A fresh ledger/controller instance must load the exact inbox fingerprint
        // from PostgreSQL rather than treating a duplicate as a new completion.
        var reloaded=new JdbcWorkflowLedger(tx(),codec());
        var freshPlane=orchestrator(reloaded,new JdbcAgentStore(tx(),codec()));
        var before=reloaded.get(TENANT,"wf-01").view();
        assertEquals(Workflow.State.TESTING,freshPlane.onBuild(builder,original).state());
        var after=reloaded.get(TENANT,"wf-01").view();
        assertEquals(before.state(),after.state());
        assertEquals(before.specDigest(),after.specDigest());
        assertEquals(1,reloaded.withUndeliveredActions().size());
        try(Connection c=dataSource.getConnection();var query=c.prepareStatement(
            "SELECT fingerprint FROM cp_event_inbox WHERE tenant_id=? AND event_id=?")) {
            query.setString(1,TENANT);query.setString(2,"durable-build-event");
            try(var rows=query.executeQuery()) {
                assertTrue(rows.next());
                assertEquals(EventIdentity.sha256(original),rows.getString(1));
                assertFalse(rows.next());
            }
        }
        var forged=new Protocol.BuildFinished(header,true,"agent-01",
            "artifact://agent-spec/evil",DIGEST,Map.of("lookup",TOOL),
            MODEL,"artifact://a2a/card",null,false);
        var denied=assertThrows(IllegalStateException.class,()->
            freshPlane.onBuild(builder,forged));
        assertEquals("EVENT_ID_COLLISION",denied.getMessage());
        assertEquals(Workflow.State.TESTING,reloaded.get(TENANT,"wf-01").view().state());
    }

    @Test void tenantWideEventIdCannotCrossWorkflowBoundaries() {
        var scope=tx();var ledger=new JdbcWorkflowLedger(scope,codec());
        var store=new JdbcAgentStore(scope,codec());
        var plane=orchestrator(ledger,store);
        plane.start(principal(),start());
        plane.start(principal(),new Protocol.Start(TENANT,"wf-02","snapshot-01","start-key-02",
            start().limits(),"trace-02"));
        var dispatcher=new OutboxDispatcher(ledger,
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> new Protocol.CommandReceipt(command.operationId(),true));
        assertEquals(2,dispatcher.dispatchPending());
        var first=new Protocol.BuildFinished(new Protocol.Header("0.1","same-event",
            TENANT,"wf-01",plane.get(principal(),TENANT,"wf-01").pendingOperationId(),
            "trace-01",NOW),true,"agent-01","artifact://agents/a1",DIGEST,
            Map.of("lookup",TOOL),MODEL,"artifact://a2a/card",null,false);
        var second=new Protocol.BuildFinished(new Protocol.Header("0.1","same-event",
            TENANT,"wf-02",plane.get(principal(),TENANT,"wf-02").pendingOperationId(),
            "trace-02",NOW),true,"agent-02","artifact://agents/a2",DIGEST,
            Map.of("lookup",TOOL),MODEL,"artifact://a2a/card",null,false);
        assertEquals(Workflow.State.TESTING,plane.onBuild(new Protocol.Principal("builder",
            TENANT,Set.of("factory:events:build")),first).state());
        var denied=assertThrows(IllegalStateException.class,()->plane.onBuild(
            new Protocol.Principal("builder",TENANT,Set.of("factory:events:build")),second));
        assertEquals("EVENT_ID_COLLISION",denied.getMessage());
        assertEquals(Workflow.State.BUILDING,ledger.get(TENANT,"wf-02").view().state());
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
    /**
     * Real loopback HTTP and PostgreSQL share one durable outbox: a new process
     * must NOT resubmit accepted remote commands merely because adapters restart.
     */
    @Test void realHttpReceiptsAreDurableAcrossFreshPostgresqlAdapters() throws Exception {
        var json=new com.fasterxml.jackson.databind.ObjectMapper();
        var builderCalls=new java.util.concurrent.atomic.AtomicInteger();
        var evalCalls=new java.util.concurrent.atomic.AtomicInteger();
        var server=com.sun.net.httpserver.HttpServer.create(
            new java.net.InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/internal/builds",exchange->{
            try {
                builderCalls.incrementAndGet();
                exchange.getRequestBody().readAllBytes();
                byte[] accepted=json.writeValueAsBytes(Map.of("build_id","build-01","status","QUEUED"));
                exchange.getResponseHeaders().set("Content-Type","application/json");
                exchange.sendResponseHeaders(202,accepted.length);
                exchange.getResponseBody().write(accepted);
            } finally { exchange.close(); }
        });
        server.createContext("/internal/evaluations",exchange->{
            try {
                evalCalls.incrementAndGet();
                var sent=json.readTree(exchange.getRequestBody());
                byte[] accepted=json.writeValueAsBytes(Map.of(
                    "evaluation_run_id",sent.path("evaluation_run_id").asText(),
                    "tenant_id",sent.path("tenant_id").asText(),"status","QUEUED"));
                exchange.getResponseHeaders().set("Content-Type","application/json");
                exchange.sendResponseHeaders(202,accepted.length);
                exchange.getResponseBody().write(accepted);
            } finally { exchange.close(); }
        });
        server.start();
        try {
            var endpoint=java.net.URI.create("http://127.0.0.1:"+server.getAddress().getPort());
            var transportBuilder=new RemoteHttpClients.Transport("builder",endpoint,
                Set.of("127.0.0.1"),true,(service,tenant)->"synthetic-token",json);
            var transportEvaluation=new RemoteHttpClients.Transport("evaluation",endpoint,
                Set.of("127.0.0.1"),true,(service,tenant)->"synthetic-token",json);
            var originScope=tx();
            var originLedger=new JdbcWorkflowLedger(originScope,codec());
            var original=orchestrator(originLedger,new JdbcAgentStore(originScope,codec()));
            original.start(principal(),start());
            var firstRelay=new OutboxDispatcher(originLedger,
                RemoteHttpClients.builder(transportBuilder),
                RemoteHttpClients.evaluator(transportEvaluation),
                c -> {throw new AssertionError("Unexpected optimizer command");},
                c -> {throw new AssertionError("Unexpected Soup command");});
            assertEquals(1,firstRelay.dispatchPending());
            assertEquals(1,builderCalls.get());

            // A new set of adapters represents process restart, not in-memory reuse.
            var restartedScope=tx();
            var restartedLedger=new JdbcWorkflowLedger(restartedScope,codec());
            var recovered=orchestrator(restartedLedger,
                new JdbcAgentStore(restartedScope,codec()));
            var replayRelay=new OutboxDispatcher(restartedLedger,
                RemoteHttpClients.builder(transportBuilder),
                RemoteHttpClients.evaluator(transportEvaluation),
                c -> {throw new AssertionError("Unexpected optimizer command");},
                c -> {throw new AssertionError("Unexpected Soup command");});
            assertEquals(0,replayRelay.dispatchPending());
            assertEquals(1,builderCalls.get());

            var header=new Protocol.Header("0.1","accepted-builder-event",TENANT,"wf-01",
                restartedLedger.get(TENANT,"wf-01").view().pendingOperationId(),"trace-01",NOW);
            assertEquals(Workflow.State.TESTING,recovered.onBuild(new Protocol.Principal(
                "builder",TENANT,Set.of("factory:events:build")),
                new Protocol.BuildFinished(header,true,"agent-01",
                    "artifact://agent-spec/v1",DIGEST,Map.of("lookup",TOOL),MODEL,
                    "artifact://a2a/card-v1",null,false)).state());
            assertEquals(1,replayRelay.dispatchPending());
            assertEquals(1,evalCalls.get());

            var finalScope=tx();
            var finalLedger=new JdbcWorkflowLedger(finalScope,codec());
            var finalRelay=new OutboxDispatcher(finalLedger,
                RemoteHttpClients.builder(transportBuilder),
                RemoteHttpClients.evaluator(transportEvaluation),
                c -> {throw new AssertionError("Unexpected optimizer command");},
                c -> {throw new AssertionError("Unexpected Soup command");});
            assertEquals(0,finalRelay.dispatchPending());
            assertEquals(1,builderCalls.get());
            assertEquals(1,evalCalls.get());
            var result=orchestrator(finalLedger,new JdbcAgentStore(finalScope,codec()))
                .onEvaluation(new Protocol.Principal("evaluator",TENANT,
                    Set.of("factory:events:evaluation")),new Protocol.EvaluationFinished(
                        new Protocol.Header("0.1","evaluation-complete",TENANT,"wf-01",
                            finalLedger.get(TENANT,"wf-01").view().pendingOperationId(),
                            "trace-01",NOW),
                        finalLedger.get(TENANT,"wf-01").view().pendingOperationId(),DIGEST,
                        forRun(evidence(),finalLedger.get(TENANT,"wf-01").view().pendingOperationId()),
                        new BigDecimal("0.1"),null,false));
            assertEquals(Workflow.State.VERIFIED,result.state());
            assertEquals(1,new JdbcAgentStore(tx(),codec()).versions(TENANT,"agent-01").size());
        } finally { server.stop(0); }
    }

    @Test void remoteHttp403PermanentlyBlocksDurableOutboxAcrossRestart() throws Exception {
        var server=com.sun.net.httpserver.HttpServer.create(
            new java.net.InetSocketAddress("127.0.0.1",0),0);
        var attempts=new java.util.concurrent.atomic.AtomicInteger();
        server.createContext("/internal/builds",exchange->{
            try {
                attempts.incrementAndGet();
                exchange.getRequestBody().readAllBytes();
                exchange.sendResponseHeaders(403,-1);
            } finally { exchange.close(); }
        });
        server.start();
        try {
            var uri=java.net.URI.create("http://127.0.0.1:"+server.getAddress().getPort());
            var transport=new RemoteHttpClients.Transport("builder",uri,Set.of("127.0.0.1"),
                true,(service,tenant)->"synthetic-token",new com.fasterxml.jackson.databind.ObjectMapper());
            var shared=tx();
            var ledger=new JdbcWorkflowLedger(shared,codec());
            orchestrator(ledger,new JdbcAgentStore(shared,codec())).start(principal(),start());
            var relay=new OutboxDispatcher(ledger,RemoteHttpClients.builder(transport),
                c -> {throw new AssertionError("Evaluation not authorized");},
                c -> {throw new AssertionError("Optimizer not authorized");},
                c -> {throw new AssertionError("Soup not authorized");});
            assertEquals(0,relay.dispatchPending());
            assertEquals(1,attempts.get());
            var recovered=new JdbcWorkflowLedger(tx(),codec());
            assertEquals(Workflow.State.BLOCKED,recovered.get(TENANT,"wf-01").view().state());
            assertEquals("REMOTE_UNAUTHORIZED",
                recovered.get(TENANT,"wf-01").view().errorCode());
            var afterRestart=new OutboxDispatcher(recovered,RemoteHttpClients.builder(transport),
                c -> {throw new AssertionError("Evaluation not authorized");},
                c -> {throw new AssertionError("Optimizer not authorized");},
                c -> {throw new AssertionError("Soup not authorized");});
            assertEquals(0,afterRestart.dispatchPending());
            assertEquals(1,attempts.get());
        } finally { server.stop(0); }
    }

    /**
     * Cross-service contract acceptance on real HTTP sockets plus PostgreSQL.
     * Tests the complete repair path with durable state after each simulated
     * application restart. The remote ports are strict local stubs, NOT
     * production Builder/Evaluation/GEPARD services.
     */
    @Test void completeBuildEvaluationGepardRetestLifecycleSurvivesRestarts() throws Exception {
        try(RemoteHttpIntegrationTest.RemoteStub builder=
                new RemoteHttpIntegrationTest.RemoteStub("/internal/builds","build_id");
            RemoteHttpIntegrationTest.RemoteStub evaluator=
                new RemoteHttpIntegrationTest.RemoteStub("/internal/evaluations","evaluation_run_id");
            RemoteHttpIntegrationTest.RemoteStub optimizer=
                new RemoteHttpIntegrationTest.RemoteStub("/internal/optimizations","optimization_run_id")) {

            var build=RemoteHttpClients.builder(builder.transport("builder"));
            var eval=RemoteHttpClients.evaluator(evaluator.transport("evaluation"));
            var optimize=RemoteHttpClients.optimizer(optimizer.transport("gepard"));
            java.util.function.Function<JdbcWorkflowLedger,OutboxDispatcher> relay=ledger ->
                new OutboxDispatcher(ledger,build,eval,optimize,
                    c->{throw new AssertionError("Soup was not requested");});
            // Ledger and AgentStore must share the SAME transaction scope.
            record Stage(JdbcWorkflowLedger ledger, ControlPlane plane, OutboxDispatcher relay) { }
            java.util.function.Supplier<Stage> stage=()->{
                var transaction=tx();
                var durableLedger=new JdbcWorkflowLedger(transaction,codec());
                var durableStore=new JdbcAgentStore(transaction,codec());
                return new Stage(durableLedger,orchestrator(durableLedger,durableStore),
                    relay.apply(durableLedger));
            };

            var stage1=stage.get();
            var l1=stage1.ledger();
            stage1.plane().start(principal(),start());
            assertEquals(1,stage1.relay().dispatchPending());
            assertEquals(1,builder.requests.size());

            var stage2=stage.get();
            var l2=stage2.ledger();
            assertEquals(0,stage2.relay().dispatchPending());
            var p2=stage2.plane();
            String buildOperation=l2.get(TENANT,"wf-01").view().pendingOperationId();
            assertEquals(Workflow.State.TESTING,p2.onBuild(
                new Protocol.Principal("builder",TENANT,Set.of("factory:events:build")),
                new Protocol.BuildFinished(
                    new Protocol.Header("0.1","build-complete",TENANT,"wf-01",
                        buildOperation,"trace-01",NOW),
                    true,"agent-01","artifact://agent-spec/v1",DIGEST,
                    Map.of("lookup",TOOL),MODEL,"artifact://a2a/card-v1",null,false)).state());
            assertEquals(1,stage2.relay().dispatchPending());
            assertEquals(1,evaluator.requests.size());

            var stage3=stage.get();
            var l3=stage3.ledger();
            assertEquals(0,stage3.relay().dispatchPending());
            String firstRun=l3.get(TENANT,"wf-01").view().pendingOperationId();
            var rejected=new AgentStore.Evidence(firstRun,DIGEST,"artifact://datasets/holdout-v1",
                DIGEST,"artifact://metrics/failure","artifact://traces/failure",
                "artifact://holdout/independent",true,false,false,true,true,
                AgentStore.Risk.HIGH,Set.of());
            assertEquals(Workflow.State.OPTIMIZING,stage3.plane().onEvaluation(
                new Protocol.Principal("evaluator",TENANT,Set.of("factory:events:evaluation")),
                new Protocol.EvaluationFinished(
                    new Protocol.Header("0.1","eval-reject",TENANT,"wf-01",
                        firstRun,"trace-01",NOW),
                    firstRun,DIGEST,rejected,new BigDecimal("0.1"),null,false)).state());
            assertEquals(1,stage3.relay().dispatchPending());
            assertEquals(1,optimizer.requests.size());

            var stage4=stage.get();
            var l4=stage4.ledger();
            assertEquals(0,stage4.relay().dispatchPending());
            String optimizeRun=l4.get(TENANT,"wf-01").view().pendingOperationId();
            String improved="sha256:"+"f".repeat(64);
            assertEquals(Workflow.State.RE_TESTING,stage4.plane().onOptimization(
                new Protocol.Principal("optimizer",TENANT,Set.of("factory:events:optimization")),
                new Protocol.OptimizationFinished(
                    new Protocol.Header("0.1","gepard-complete",TENANT,"wf-01",
                        optimizeRun,"trace-01",NOW),
                    true,DIGEST,"artifact://agents/improved-v2",improved,
                    new BigDecimal("0.2"),null,false)).state());
            assertEquals(1,stage4.relay().dispatchPending());
            assertEquals(2,evaluator.requests.size());

            var stage5=stage.get();
            var l5=stage5.ledger();
            assertEquals(0,stage5.relay().dispatchPending());
            String finalRun=l5.get(TENANT,"wf-01").view().pendingOperationId();
            var approved=new AgentStore.Evidence(finalRun,improved,
                "artifact://datasets/holdout-v1",DIGEST,"artifact://metrics/pass",
                "artifact://traces/pass","artifact://holdout/independent",
                true,true,false,true,true,AgentStore.Risk.HIGH,Set.of());
            assertEquals(Workflow.State.VERIFIED,stage5.plane().onEvaluation(
                new Protocol.Principal("evaluator",TENANT,Set.of("factory:events:evaluation")),
                new Protocol.EvaluationFinished(
                    new Protocol.Header("0.1","eval-pass",TENANT,"wf-01",
                        finalRun,"trace-01",NOW),
                    finalRun,improved,approved,new BigDecimal("0.2"),null,false)).state());

            var finalStage=stage.get();
            var durable=finalStage.ledger();
            assertEquals(0,finalStage.relay().dispatchPending());
            assertEquals(Workflow.State.VERIFIED,
                durable.get(TENANT,"wf-01").view().state());
            assertEquals(1,new JdbcAgentStore(tx(),codec())
                .versions(TENANT,"agent-01").size());
            assertEquals(1,builder.requests.size());
            assertEquals(1,optimizer.requests.size());
            assertEquals(2,evaluator.requests.size());
        }
    }

    @Test void isolatedRailwayPocSchemaBootstrapIsTransactionalAndIdempotent() throws Exception {
        // Run only on the disposable test database selected by prepareSchema().
        // The production service is never connected to this JUnit suite.
        try {
            JdbcPocSchemaBootstrap.bootstrap(dataSource);
            JdbcPocSchemaBootstrap.bootstrap(dataSource);
            try (Connection c=dataSource.getConnection();var s=c.createStatement()) {
                try(var rs=s.executeQuery(
                    "SELECT COUNT(*) FROM cp_factory_poc.cp_schema_migration")) {
                    assertTrue(rs.next());
                    assertEquals(2,rs.getInt(1));
                }
                try(var rs=s.executeQuery(
                    "SELECT boots FROM cp_factory_poc.cp_poc_restart_probe "
                    + "WHERE probe_key='schema-liveness'")) {
                    assertTrue(rs.next());
                    assertEquals(2,rs.getLong(1));
                }
                try(var rs=s.executeQuery(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    + "WHERE table_schema='cp_factory_poc' "
                    + "AND table_name IN ('cp_workflow','cp_agent_lock','cp_agent_version',"
                    + "'cp_agent_operation','cp_agent_transition','cp_event_inbox')")) {
                    assertTrue(rs.next());
                    assertEquals(6,rs.getInt(1));
                }
            }
        } finally {
            try(Connection c=dataSource.getConnection();var s=c.createStatement()) {
                s.execute("DROP SCHEMA IF EXISTS cp_factory_poc CASCADE");
            }
        }
    }

    @Test void brokenPocSchemaConnectionDoesNotExposeJdbcCredentials() throws Exception {
        var broken=org.mockito.Mockito.mock(DataSource.class);
        org.mockito.Mockito.when(broken.getConnection())
            .thenThrow(new java.sql.SQLException(
                "secret-token jdbc:postgresql://internal-account:5432/production"));
        var error=assertThrows(IllegalStateException.class,
            ()->JdbcPocSchemaBootstrap.bootstrap(broken));
        assertEquals("POC_DATABASE_UNAVAILABLE",error.getMessage());
        assertNull(error.getCause());
    }
}
