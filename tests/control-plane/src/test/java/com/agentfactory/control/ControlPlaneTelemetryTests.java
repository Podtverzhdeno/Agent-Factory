package com.agentfactory.control;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

/**
 * Dependency-free regression suite: operational logs must be useful without
 * exposing tokens, attacker-controlled identifiers or remote error messages.
 */
public final class ControlPlaneTelemetryTests {
    private ControlPlaneTelemetryTests() { }
    private static final String TENANT="confidential-tenant-token", WF="workflow-private-id";
    private static final String CORRELATION="trace\nBearer secret-value";
    private static final Instant NOW=Instant.parse("2026-10-27T09:00:00Z");

    private static void check(boolean ok) {
        if(!ok) throw new AssertionError("CONTROL_PLANE_TELEMETRY_ASSERTION_FAILED");
    }
    private static Workflow pending() {
        var req=new Protocol.Start(TENANT,WF,"snapshot-private","idempotency-key",
            new Protocol.Limits(2,new BigDecimal("4.0"),NOW.plusSeconds(3600)),CORRELATION);
        var snap=new Protocol.Snapshot(TENANT,"snapshot-private","READY",
            "sha256:"+"a".repeat(64),"artifact://policies/secret",
            "artifact://datasets/secret","operator","rev-1");
        var w=new Workflow(req,snap);
        w.state=Workflow.State.BUILDING;
        w.enqueue(Workflow.ActionType.BUILD,null,null);
        return w;
    }
    private static final class Capture implements AutoCloseable {
        private final Logger logger=Logger.getLogger(ControlPlaneTelemetry.class.getName());
        private final Level oldLevel=logger.getLevel();
        private final boolean oldParent=logger.getUseParentHandlers();
        private final List<LogRecord> records=new ArrayList<>();
        private final Handler handler=new Handler() {
            @Override public void publish(LogRecord record) { records.add(record); }
            @Override public void flush() { }
            @Override public void close() { }
        };
        Capture() {
            handler.setLevel(Level.ALL);
            logger.setLevel(Level.ALL);
            logger.setUseParentHandlers(false);
            logger.addHandler(handler);
        }
        List<LogRecord> records() { return records; }
        @Override public void close() {
            logger.removeHandler(handler);
            logger.setUseParentHandlers(oldParent);
            logger.setLevel(oldLevel);
        }
    }
    private static void noSecrets(String message) {
        for(String secret:List.of(TENANT,WF,CORRELATION,"Bearer","secret-value",
            "artifact://","jdbc:","raw-remote")) check(!message.contains(secret));
    }

    public static void logsAcceptedCommandWithoutRawIds() {
        var w=pending();
        try(var captured=new Capture()) {
            ControlPlaneTelemetry.outbox(ControlPlaneTelemetry.Outcome.ACKNOWLEDGED,
                w,w.actions.getFirst(),1,null);
            check(captured.records().size()==1);
            String message=captured.records().getFirst().getMessage();
            check(message.contains("event=control_plane.outbox"));
            check(message.contains("outcome=ACKNOWLEDGED"));
            check(message.contains("action=BUILD"));
            check(message.contains("attempts=1"));
            check(message.contains("workflow_ref="));
            noSecrets(message);
        }
    }

    public static void restrictsRemoteCodesAndCapsAttempts() {
        var w=pending();
        try(var captured=new Capture()) {
            ControlPlaneTelemetry.outbox(ControlPlaneTelemetry.Outcome.BLOCKED,
                w,w.actions.getFirst(),100,"SUPERSECRET_PASSWORD_IN_UPPERCASE");
            check(captured.records().size()==1);
            var record=captured.records().getFirst();
            check(record.getLevel()==Level.WARNING);
            check(record.getMessage().contains("code=OTHER_FAILURE"));
            check(record.getMessage().contains("attempts=5"));
            check(!record.getMessage().contains("SUPERSECRET_PASSWORD"));
            ControlPlaneTelemetry.outbox(ControlPlaneTelemetry.Outcome.RETRY_SCHEDULED,
                w,w.actions.getFirst(),3,"REMOTE_UNAVAILABLE");
            check(captured.records().getLast().getMessage().contains("code=REMOTE_UNAVAILABLE"));
            noSecrets(captured.records().getLast().getMessage());
        }
    }

    public static void saltedReferencesDoNotEmbedIdentifiers() {
        String one=ControlPlaneTelemetry.ref(TENANT+":"+WF);
        check(one.equals(ControlPlaneTelemetry.ref(TENANT+":"+WF)));
        check(!one.equals(ControlPlaneTelemetry.ref(TENANT+":other-workflow")));
        check(one.matches("[0-9a-f]{16}"));
        check(!one.contains(WF) && !one.contains(TENANT));
    }

    public static void logsCommittedLifecycleNotificationsOnly() {
        var ledger=new InMemoryWorkflowLedger();
        var workflow=pending();
        workflow.audit.add(new Workflow.Audit(NOW,Workflow.State.READY,
            Workflow.State.BUILDING,"attacker-raw-remote-secret",CORRELATION));
        ledger.open(workflow);
        var publishes=new AtomicInteger();
        var relay=new LifecycleEventDispatcher(ledger,event -> publishes.incrementAndGet());
        try(var captured=new Capture()) {
            check(relay.publishPending()==1);
            check(relay.publishPending()==0);
            check(publishes.get()==1);
            check(captured.records().size()==1);
            var message=captured.records().getFirst().getMessage();
            check(message.contains("event=control_plane.lifecycle"));
            check(message.contains("outcome=PUBLISHED"));
            check(message.contains("from=READY"));
            check(message.contains("to=BUILDING"));
            check(message.contains("sequence=1"));
            noSecrets(message);
        }
    }

    public static void failedPublisherIsLoggedButFailureRetainsReplay() {
        var ledger=new InMemoryWorkflowLedger();
        var w=pending();
        w.audit.add(new Workflow.Audit(NOW,Workflow.State.DRAFT,
            Workflow.State.BUILDING,"secret-raw-remote",CORRELATION));
        ledger.open(w);
        var relay=new LifecycleEventDispatcher(ledger,event -> {
            throw new IllegalStateException("raw-remote private credential and SQL");
        });
        try(var captured=new Capture()) {
            try {
                relay.publishPending();
                throw new AssertionError("expected publisher failure");
            } catch(IllegalStateException expected) {
                check(expected.getMessage().contains("private credential"));
            }
            check(ledger.get(TENANT,WF).publishedAuditCount==0);
            check(captured.records().size()==1);
            var record=captured.records().getFirst();
            check(record.getLevel()==Level.WARNING);
            check(record.getMessage().contains("outcome=PUBLISH_FAILED"));
            noSecrets(record.getMessage());
            check(!record.getMessage().contains("private credential"));
        }
    }

    public static void dispatchOutcomesAreLoggedAfterLedgerCommit() {
        var ledger=new InMemoryWorkflowLedger();
        ledger.open(pending());
        var relay=new OutboxDispatcher(ledger,
            command -> new Protocol.CommandReceipt(command.operationId(),true),
            command -> {throw new AssertionError("Unexpected Evaluation");},
            command -> {throw new AssertionError("Unexpected GEPARD");},
            command -> {throw new AssertionError("Unexpected Soup");});
        try(var captured=new Capture()) {
            check(relay.dispatchPending()==1);
            check(ledger.get(TENANT,WF).actions.getFirst().delivered);
            check(captured.records().stream().anyMatch(r ->
                r.getMessage().contains("outcome=ACKNOWLEDGED")));
            for(LogRecord record:captured.records()) noSecrets(record.getMessage());
        }
    }

    public static void main(String[] args) {
        logsAcceptedCommandWithoutRawIds();
        restrictsRemoteCodesAndCapsAttempts();
        saltedReferencesDoNotEmbedIdentifiers();
        logsCommittedLifecycleNotificationsOnly();
        failedPublisherIsLoggedButFailureRetainsReplay();
        dispatchOutcomesAreLoggedAfterLedgerCommit();
        System.out.println("CONTROL PLANE TELEMETRY TESTS PASSED: 6");
    }
}
