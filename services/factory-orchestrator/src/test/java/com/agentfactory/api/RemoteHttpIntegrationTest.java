package com.agentfactory.api;

import com.agentfactory.control.*;
import com.agentfactory.store.AgentStore;
import com.agentfactory.store.InMemoryAgentStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Actual HTTP transport integration against three independent local HTTP servers.
 * Does NOT claim compatibility with team 04/05 deployed production services.
 */
final class RemoteHttpIntegrationTest {
    static final String TENANT="tenant-a";
    static final String HASH="sha256:"+"a".repeat(64);
    static final String MODEL="sha256:"+"b".repeat(64);
    static final Instant NOW=Instant.parse("2026-10-27T09:00:00Z");
    static final Protocol.Principal HUMAN=new Protocol.Principal("human",TENANT,
        Set.of("factory:start","factory:read","factory:release"));
    static final Protocol.Principal BUILDER=new Protocol.Principal("builder",TENANT,Set.of("factory:events:build"));
    static final Protocol.Principal EVALUATOR=new Protocol.Principal("evaluator",TENANT,Set.of("factory:events:evaluation"));
    static final Protocol.Principal OPTIMIZER=new Protocol.Principal("optimizer",TENANT,Set.of("factory:events:optimization"));

    static final class RemoteStub implements AutoCloseable {
        final HttpServer server;
        final List<String> requests=new ArrayList<>();
        final String path;
        final String receiptId;
        volatile boolean forgedOperationId;
        volatile boolean forgedEvaluationRunId;
        volatile boolean forgedEvaluationTenant;
        volatile boolean oversizedReceipt;
        RemoteStub(String path,String receiptId) throws Exception {
            this.path=path;this.receiptId=receiptId;
            server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
            server.createContext(path,exchange->{
                try {
                    String requestJson=new String(exchange.getRequestBody().readAllBytes(),StandardCharsets.UTF_8);
                    requests.add(requestJson);
                    // Evaluation team 05 accepts caller-generated evaluation_run_id,
                    // unlike the independently assigned build_id.
                    String receiptValue="evaluation_run_id".equals(receiptId)
                        ? new ObjectMapper().readTree(requestJson).path("evaluation_run_id").asText("")
                        : "accepted-001";
                    if(forgedEvaluationRunId) receiptValue="wrong-run-id";
                    if(oversizedReceipt) receiptValue="x".repeat(9_000);
                    String response="{\""+receiptId+"\":\""+receiptValue+"\",\"status\":\"QUEUED\""+
                        ("evaluation_run_id".equals(receiptId)?
                            ",\"tenant_id\":\""+(forgedEvaluationTenant?"foreign-tenant":"tenant-a")+"\"":"")+
                        (forgedOperationId?",\"operation_id\":\"wrong-operation\"":"")+"}";
                    byte[] body=response.getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().set("Content-Type","application/json");
                    if(!"Bearer synthetic-test-token".equals(exchange.getRequestHeaders().getFirst("Authorization")) ||
                        exchange.getRequestHeaders().getFirst("Idempotency-Key")==null ||
                        exchange.getRequestHeaders().getFirst("X-Correlation-ID")==null) {
                        exchange.sendResponseHeaders(403,-1);
                    } else {
                        exchange.sendResponseHeaders(202,body.length);
                        exchange.getResponseBody().write(body);
                    }
                } finally { exchange.close(); }
            });
            server.start();
        }
        RemoteHttpClients.Transport transport(String name) {
            return new RemoteHttpClients.Transport(name,
                URI.create("http://127.0.0.1:"+server.getAddress().getPort()),
                Set.of("127.0.0.1"),true,(service,tenant)->"synthetic-test-token",
                new ObjectMapper());
        }
        @Override public void close(){ server.stop(0); }
    }
    static Protocol.Header header(String event,ControlPlane plane) {
        String pending=plane.get(HUMAN,TENANT,"wf-01").pendingOperationId();
        return new Protocol.Header("0.1",event,TENANT,"wf-01",pending,"correlation-01",NOW);
    }
    static AgentStore.Evidence evidence(String digest,boolean pass) {
        return new AgentStore.Evidence("eval-01",digest,"artifact://datasets/v1",HASH,
            "artifact://metrics/v1","artifact://traces/v1","artifact://holdout/v1",
            true,pass,false,true,true,AgentStore.Risk.HIGH,Set.of());
    }
    @Test void completeRepairLifecycleCallsDistinctRemoteHttpServices() throws Exception {
        try(RemoteStub builder=new RemoteStub("/internal/builds","build_id");
            RemoteStub evaluator=new RemoteStub("/internal/evaluations","evaluation_run_id");
            RemoteStub optimizer=new RemoteStub("/internal/optimizations","optimization_run_id")) {
            var ledger=new InMemoryWorkflowLedger();
            var store=new InMemoryAgentStore();
            var plane=new ControlPlane(ledger,(tenant,snapshot)->
                new Protocol.Snapshot(tenant,snapshot,"READY",HASH,"artifact://policies/v1",
                    "artifact://datasets/v1","human","v1"),
                (actor,tenant,scope)->{
                    if(!tenant.equals(actor.tenantId()) || !actor.scopes().contains(scope))
                        throw new IllegalStateException("UNAUTHORIZED_TENANT_OR_SCOPE");
                },
                (tenant,w,purpose)->true,view->false,()->NOW,store,
                (tenant,run,digest,result)-> {
                    if(!TENANT.equals(tenant) || !digest.equals(result.specDigest()))
                        throw new IllegalStateException("ATTESTATION_FAILED");
                });
            var dispatcher=new OutboxDispatcher(ledger,
                RemoteHttpClients.builder(builder.transport("builder")),
                RemoteHttpClients.evaluator(evaluator.transport("evaluation")),
                RemoteHttpClients.optimizer(optimizer.transport("gepard")),
                c -> {throw new AssertionError("Soup was not requested");});
            var started=plane.start(HUMAN,new Protocol.Start(TENANT,"wf-01","snapshot-01","start-key",
                new Protocol.Limits(1,new BigDecimal("3"),NOW.plusSeconds(3600)),"correlation-01"));
            assertEquals(Workflow.State.BUILDING,started.state());
            assertEquals(1,dispatcher.dispatchPending());
            plane.onBuild(BUILDER,new Protocol.BuildFinished(header("build-done",plane),true,
                "agent-01","artifact://agents/first",HASH,Map.of("lookup",HASH),
                MODEL,"artifact://a2a/agent",null,false));
            assertEquals(1,dispatcher.dispatchPending());
            var failure=plane.onEvaluation(EVALUATOR,new Protocol.EvaluationFinished(header("eval-fail",plane),
                "eval-01",HASH,evidence(HASH,false),new BigDecimal("0.1"),null,false));
            assertEquals(Workflow.State.OPTIMIZING,failure.state());
            assertEquals(1,dispatcher.dispatchPending());
            String improved="sha256:"+"c".repeat(64);
            plane.onOptimization(OPTIMIZER,new Protocol.OptimizationFinished(header("optimized",plane),
                true,HASH,"artifact://agents/improved",improved,new BigDecimal("0.2"),null,false));
            assertEquals(1,dispatcher.dispatchPending());
            var finalState=plane.onEvaluation(EVALUATOR,new Protocol.EvaluationFinished(header("eval-pass",plane),
                "eval-01",improved,evidence(improved,true),new BigDecimal("0.2"),null,false));
            assertEquals(Workflow.State.VERIFIED,finalState.state());
            assertEquals(1,builder.requests.size());
            assertEquals(2,evaluator.requests.size());
            // Match actual strict EvaluationRequestBody from workstream 05.
            var evaluationRequest=new ObjectMapper().readTree(evaluator.requests.getFirst());
            assertEquals(7,evaluationRequest.size());
            assertEquals(TENANT,evaluationRequest.path("tenant_id").asText());
            assertEquals("artifact://agents/first",evaluationRequest.path("agent_spec_ref").asText());
            assertEquals(HASH,evaluationRequest.path("agent_spec_digest").asText());
            assertEquals("artifact://datasets/v1",evaluationRequest.path("dataset_version_ref").asText());
            assertEquals("artifact://policies/v1",evaluationRequest.path("policy_ref").asText());
            assertTrue(evaluationRequest.path("evaluation_run_id").asText().contains("evaluate"));
            assertTrue(evaluationRequest.path("idempotency_key").asText().startsWith("control:"));
            assertFalse(evaluationRequest.has("operation_id"));
            assertFalse(evaluationRequest.has("baseline_spec_digest"));
            assertFalse(evaluationRequest.has("schema_version"));

            assertEquals(1,optimizer.requests.size());
            assertTrue(builder.requests.getFirst().contains("\"tenant_id\":\"tenant-a\""));
            assertTrue(optimizer.requests.getFirst().contains("\"baseline_spec_ref\""));
            assertTrue(store.active(TENANT,"agent-01").isEmpty());
            assertEquals(Workflow.State.RELEASED,plane.release(HUMAN,TENANT,"wf-01","approved-v1").state());
            assertTrue(store.active(TENANT,"agent-01").isPresent());
        }
    }
    @Test void rejectEvaluationReceiptForAnotherTenant() throws Exception {
        try(RemoteStub evaluator=new RemoteStub("/internal/evaluations","evaluation_run_id")) {
            evaluator.forgedEvaluationTenant=true;
            var command=new Protocol.EvaluationCommand(TENANT,"wf-01","eval-request-tenant-01",
                "artifact://agents/first",HASH,HASH,"artifact://datasets/v1",
                "artifact://policies/v1","control:eval-tenant-01","corr-01");
            var error=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.evaluator(evaluator.transport("evaluation")).submit(command));
            assertEquals("REMOTE_RECEIPT_MISMATCH",error.getMessage());
            assertFalse(error.retryable());
        }
    }

    @Test void rejectEvaluationReceiptForAnotherRunId() throws Exception {
        try(RemoteStub evaluator=new RemoteStub("/internal/evaluations","evaluation_run_id")) {
            evaluator.forgedEvaluationRunId=true;
            var command=new Protocol.EvaluationCommand(TENANT,"wf-01","eval-request-01",
                "artifact://agents/first",HASH,HASH,"artifact://datasets/v1",
                "artifact://policies/v1","control:eval-01","corr-01");
            var error=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.evaluator(evaluator.transport("evaluation")).submit(command));
            assertEquals("REMOTE_RECEIPT_MISMATCH",error.getMessage());
            assertFalse(error.retryable());
        }
    }

    @Test void rejectsReceiptEchoingAnotherOperationId() throws Exception {
        try(RemoteStub builder=new RemoteStub("/internal/builds","build_id")) {
            builder.forgedOperationId=true;
            var command=new Protocol.BuildCommand(TENANT,"wf-01","snapshot-01",
                HASH,"operation-01","idempotency-01","correlation-01",
                "artifact://policy/v1");
            var error=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.builder(builder.transport("builder")).submit(command));
            assertEquals("REMOTE_RECEIPT_MISMATCH",error.getMessage());
            assertFalse(error.retryable());
            assertEquals(1,builder.requests.size());
        }
    }

    @Test void forbiddenHttpReplyIsPermanent() throws Exception {
        try(RemoteStub builder=new RemoteStub("/internal/builds","build_id")) {
            var endpoint=new RemoteHttpClients.Transport("builder",
                URI.create("http://127.0.0.1:"+builder.server.getAddress().getPort()),
                Set.of("127.0.0.1"),true,
                (service,tenant)->"synthetic-wrong-token",new ObjectMapper());
            var failure=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.builder(endpoint).submit(new Protocol.BuildCommand(
                    TENANT,"wf-01","snapshot-01",HASH,"op-01","idempotency-01",
                    "corr-01","artifact://policy/v1")));
            assertFalse(failure.retryable());
            assertEquals("REMOTE_UNAUTHORIZED",failure.getMessage());
            assertEquals(1,builder.requests.size());
        }
    }


    @Test void non202SuccessOrRedirectDoesNotRetryExternalSideEffects() throws Exception {
        for(int statusCode : List.of(200,302)) {
            HttpServer server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
            var attempts=new java.util.concurrent.atomic.AtomicInteger();
            server.createContext("/internal/builds", exchange -> {
                attempts.incrementAndGet();
                if(statusCode==302) {
                    // A redirect must never make a credentialled second request.
                    exchange.getResponseHeaders().set("Location","http://169.254.169.254/latest/meta-data/");
                    exchange.sendResponseHeaders(302,-1);
                } else {
                    byte[] receipt="{\\"build_id\\":\\"external-id\\",\\"status\\":\\"QUEUED\\"}"
                        .getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().set("Content-Type","application/json");
                    exchange.sendResponseHeaders(200,receipt.length);
                    exchange.getResponseBody().write(receipt);
                }
                exchange.close();
            });
            server.start();
            try {
                var transport=new RemoteHttpClients.Transport("builder",
                    URI.create("http://127.0.0.1:"+server.getAddress().getPort()),
                    Set.of("127.0.0.1"),true,
                    (service,tenant)->"synthetic-test-token",new ObjectMapper());
                var command=new Protocol.BuildCommand(TENANT,"wf-01","snapshot-01",
                    HASH,"operation-01","idempotency-01","correlation-01","artifact://policy/v1");
                var error=assertThrows(Protocol.RemoteCommandFailure.class,()->
                    RemoteHttpClients.builder(transport).submit(command));
                assertEquals("REMOTE_COMMAND_REJECTED",error.getMessage());
                assertFalse(error.retryable());
                assertEquals(1,attempts.get());
            } finally { server.stop(0); }
        }
    }

    @Test void http202WithoutJsonMediaTypeCannotAcknowledgeCommand() throws Exception {
        HttpServer server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        var attempts=new java.util.concurrent.atomic.AtomicInteger();
        server.createContext("/internal/builds", exchange -> {
            attempts.incrementAndGet();
            byte[] receipt="{\\"build_id\\":\\"external-id\\",\\"status\\":\\"QUEUED\\"}"
                .getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type","text/plain");
            exchange.sendResponseHeaders(202,receipt.length);
            exchange.getResponseBody().write(receipt);
            exchange.close();
        });
        server.start();
        try {
            var transport=new RemoteHttpClients.Transport("builder",
                URI.create("http://127.0.0.1:"+server.getAddress().getPort()),
                Set.of("127.0.0.1"),true,
                (service,tenant)->"synthetic-test-token",new ObjectMapper());
            var command=new Protocol.BuildCommand(TENANT,"wf-01","snapshot-01",
                HASH,"operation-01","idempotency-01","correlation-01","artifact://policy/v1");
            var error=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.builder(transport).submit(command));
            assertEquals("REMOTE_RECEIPT_INVALID",error.getMessage());
            assertFalse(error.retryable());
            assertEquals(1,attempts.get());
        } finally { server.stop(0); }
    }

    @Test void unavailableHttpReplyIsRetryableWithoutAutomaticRepetition() throws Exception {
        HttpServer unavailable=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        var deliveries=new java.util.concurrent.atomic.AtomicInteger();
        unavailable.createContext("/internal/builds",exchange->{
            deliveries.incrementAndGet();
            exchange.sendResponseHeaders(503,-1);
            exchange.close();
        });
        unavailable.start();
        try {
            var endpoint=new RemoteHttpClients.Transport("builder",
                URI.create("http://127.0.0.1:"+unavailable.getAddress().getPort()),
                Set.of("127.0.0.1"),true,
                (service,tenant)->"synthetic-test-token",new ObjectMapper());
            var failure=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.builder(endpoint).submit(new Protocol.BuildCommand(
                    TENANT,"wf-01","snapshot-01",HASH,"op-01","idempotency-01",
                    "corr-01","artifact://policy/v1")));
            assertTrue(failure.retryable());
            assertEquals("REMOTE_UNAVAILABLE",failure.getMessage());
            assertEquals(1,deliveries.get());
        } finally { unavailable.stop(0); }
    }

    @Test void oversizedReceiptIsRejectedBeforeParsingAndNeverRetried() throws Exception {
        try(RemoteStub builder=new RemoteStub("/internal/builds","build_id")) {
            builder.oversizedReceipt=true;
            var failure=assertThrows(Protocol.RemoteCommandFailure.class,()->
                RemoteHttpClients.builder(builder.transport("builder")).submit(
                    new Protocol.BuildCommand(TENANT,"wf-01","snapshot-01",HASH,
                        "operation-01","idempotency-01","correlation-01","artifact://policy/v1")));
            assertEquals("REMOTE_RECEIPT_INVALID",failure.getMessage());
            assertFalse(failure.retryable());
            assertEquals(1,builder.requests.size());
        }
    }

    @Test void relativeEndpointCannotBypassHostAndTlsChecks() {
        assertThrows(IllegalArgumentException.class,()->new RemoteHttpClients.Transport(
            "builder",URI.create("/internal/builds"),Set.of("localhost"),false,
            (service,tenant)->"synthetic-token",new ObjectMapper()));
        assertThrows(IllegalArgumentException.class,()->new RemoteHttpClients.Transport(
            "builder",URI.create("https://builder.example.invalid"),null,false,
            (service,tenant)->"synthetic-token",new ObjectMapper()));
    }

    @Test void endpointAllowlistDeniesArbitraryOutboundHost() {
        assertThrows(IllegalArgumentException.class,()->new RemoteHttpClients.Transport("builder",
            URI.create("http://169.254.169.254:80"),Set.of("169.254.169.254"),true,
            (service,tenant)->"token",new ObjectMapper()));
        assertThrows(IllegalArgumentException.class,()->new RemoteHttpClients.Transport("builder",
            URI.create("https://builder.example.invalid"),Set.of("evaluation.example.invalid"),
            false,(service,tenant)->"token",new ObjectMapper()));
    }
}
