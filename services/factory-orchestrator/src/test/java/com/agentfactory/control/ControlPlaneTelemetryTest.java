package com.agentfactory.control;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import org.junit.jupiter.api.Test;

/**
 * Regression tests for private-by-design operational audit logs. No raw
 * tenant/workflow/operation/correlation IDs or exception messages may leak.
 */
final class ControlPlaneTelemetryTest {
    private static final String TENANT="tenant-sensitive-billing-team";
    private static final String WORKFLOW="customer-project-secret-wf";
    private static final String CORRELATION="private-correlation-1234";

    private static InMemoryWorkflowLedger pending() {
        var l=new InMemoryWorkflowLedger();
        var req=new Protocol.Start(TENANT,WORKFLOW,"sensitive-snapshot","private-start-key",
            new Protocol.Limits(1,new BigDecimal("1"),Instant.parse("2028-01-01T00:00:00Z")),
            CORRELATION);
        var snapshot=new Protocol.Snapshot(TENANT,"sensitive-snapshot","READY",
            "sha256:"+"a".repeat(64),"artifact://policies/private",
            "artifact://datasets/private","tester","rev-1");
        var workflow=new Workflow(req,snapshot);
        workflow.state=Workflow.State.BUILDING;
        workflow.enqueue(Workflow.ActionType.BUILD,null,null);
        l.open(workflow);
        return l;
    }

    private static OutboxDispatcher dispatcher(InMemoryWorkflowLedger ledger, Ports.BuildClient builder) {
        return new OutboxDispatcher(ledger,builder,
            c->{throw new AssertionError("No evaluation");},
            c->{throw new AssertionError("No optimizer");},
            c->{throw new AssertionError("No Soup");});
    }

    private static List<LogRecord> capture(Runnable run) {
        var result=new ArrayList<LogRecord>();
        Logger logger=Logger.getLogger(ControlPlaneTelemetry.class.getName());
        Level initial=logger.getLevel();
        boolean useParent=logger.getUseParentHandlers();
        Handler handler=new Handler() {
            @Override public void publish(LogRecord record) { result.add(record); }
            @Override public void flush() { }
            @Override public void close() { }
        };
        handler.setLevel(Level.ALL);
        logger.addHandler(handler);
        logger.setLevel(Level.ALL);
        logger.setUseParentHandlers(false);
        try { run.run(); }
        finally {
            logger.removeHandler(handler);
            logger.setLevel(initial);
            logger.setUseParentHandlers(useParent);
        }
        return List.copyOf(result);
    }

    private static String onlyMessage(List<LogRecord> records) {
        assertEquals(1,records.size(),"Expected a single bounded outcome event");
        var record=records.getFirst();
        assertNull(record.getThrown(),"Stack traces are forbidden in audit telemetry");
        String message=record.getMessage();
        assertTrue(message.startsWith("event=control_plane.outbox "));
        assertTrue(message.contains(" action=BUILD "));
        assertTrue(message.matches(".* workflow_ref=[a-f0-9]{16} .*"));
        assertTrue(message.matches(".* operation_ref=[a-f0-9]{16} .*"));
        assertTrue(message.matches(".* correlation_ref=[a-f0-9]{16} .*"));
        for(String forbidden:List.of(TENANT,WORKFLOW,CORRELATION,
            "private-start-key","sensitive-snapshot","artifact://")) {
            assertFalse(message.contains(forbidden),"Raw sensitive data was logged");
        }
        return message;
    }

    @Test void acceptedCommandLogsOneRedactedReceiptAndDoesNotReemit() {
        var ledger=pending();
        var logs=capture(()->{
            assertEquals(1,dispatcher(ledger,c->new Protocol.CommandReceipt(
                c.operationId(),true)).dispatchPending());
            assertEquals(0,dispatcher(ledger,c->{throw new AssertionError("Replay");})
                .dispatchPending());
        });
        assertTrue(onlyMessage(logs).contains("outcome=ACKNOWLEDGED"));
        assertEquals(Level.INFO,logs.getFirst().getLevel());
    }

    @Test void transientFailureLogsRetryCodeButNeverExceptionDetails() {
        var ledger=pending();
        var logs=capture(()->assertEquals(0,dispatcher(ledger,
            c->{throw new IllegalStateException("Authorization: Bearer secret-token-value");})
            .dispatchPending()));
        var event=onlyMessage(logs);
        assertTrue(event.contains("outcome=RETRY_SCHEDULED"));
        assertTrue(event.contains(" attempts=1 "));
        assertTrue(event.contains("code=REMOTE_DISPATCH_EXCEPTION"));
        assertFalse(event.contains("secret-token-value"));
        assertEquals(1,ledger.get(TENANT,WORKFLOW).actions.getFirst().attempts);
    }

    @Test void remoteRetryableFailureLogsOnlyApprovedErrorCode() {
        var ledger=pending();
        var logs=capture(()->assertEquals(0,dispatcher(ledger,
            c->{throw new Protocol.RemoteCommandFailure("REMOTE_UNAVAILABLE",true);})
            .dispatchPending()));
        assertTrue(onlyMessage(logs).contains("code=REMOTE_UNAVAILABLE"));
    }

    @Test void permanent403BlocksAndEmitsOneWarningWithoutRawIds() {
        var ledger=pending();
        var records=capture(()->{
            assertEquals(0,dispatcher(ledger,c->{
                throw new Protocol.RemoteCommandFailure("REMOTE_UNAUTHORIZED",false);
            }).dispatchPending());
            assertEquals(0,dispatcher(ledger,c->{throw new AssertionError("Should not retry");})
                .dispatchPending());
        });
        assertEquals(Level.WARNING,records.getFirst().getLevel());
        String event=onlyMessage(records);
        assertTrue(event.contains("outcome=BLOCKED"));
        assertTrue(event.contains(" attempts=5 "));
        assertTrue(event.contains("code=REMOTE_UNAUTHORIZED"));
        assertEquals(Workflow.State.BLOCKED,ledger.get(TENANT,WORKFLOW).state);
    }

    @Test void retryBudgetExhaustionIsLoggedOnceOnFifthAttempt() {
        var ledger=pending();
        ledger.transact(TENANT,WORKFLOW,w->{w.actions.getFirst().attempts=4;return null;});
        var logs=capture(()->assertEquals(0,dispatcher(ledger,c->{
            throw new Protocol.RemoteCommandFailure("REMOTE_UNAVAILABLE",true);
        }).dispatchPending()));
        assertTrue(onlyMessage(logs).contains("outcome=BLOCKED"));
        assertTrue(logs.getFirst().getMessage().contains("code=OUTBOX_DELIVERY_EXHAUSTED"));
        assertEquals(Workflow.State.BLOCKED,ledger.get(TENANT,WORKFLOW).state);
    }

    @Test void staleSuccessDoesNotClaimAckOrReopenWorkflow() {
        var ledger=pending();
        var logs=capture(()->assertEquals(0,dispatcher(ledger,c->{
            ledger.transact(TENANT,WORKFLOW,w->{
                w.state=Workflow.State.BLOCKED;
                w.errorCode="TIME_BUDGET_EXHAUSTED";
                w.pendingOperationId=null;
                return null;
            });
            return new Protocol.CommandReceipt(c.operationId(),true);
        }).dispatchPending()));
        assertTrue(onlyMessage(logs).contains("outcome=SUPERSEDED"));
        assertEquals(Level.FINE,logs.getFirst().getLevel());
        assertEquals("TIME_BUDGET_EXHAUSTED",ledger.get(TENANT,WORKFLOW).errorCode);
    }

    @Test void staleExceptionIsNotLoggedAsRemoteErrorOrNewBlock() {
        var ledger=pending();
        var logs=capture(()->assertEquals(0,dispatcher(ledger,c->{
            ledger.transact(TENANT,WORKFLOW,w->{
                w.state=Workflow.State.BLOCKED;
                w.errorCode="TIME_BUDGET_EXHAUSTED";
                w.pendingOperationId=null;
                return null;
            });
            throw new IllegalStateException("topsecret developer auth");
        }).dispatchPending()));
        assertTrue(onlyMessage(logs).contains("outcome=SUPERSEDED"));
        assertFalse(logs.getFirst().getMessage().contains("topsecret"));
        assertEquals("TIME_BUDGET_EXHAUSTED",ledger.get(TENANT,WORKFLOW).errorCode);
    }

    @Test void mismatchedReceiptBlocksAndLogsProtocolCode() {
        var ledger=pending();
        var logs=capture(()->assertEquals(0,dispatcher(ledger,
            c->new Protocol.CommandReceipt("another-tenants-operation",true)).dispatchPending()));
        var event=onlyMessage(logs);
        assertTrue(event.contains("outcome=BLOCKED"));
        assertTrue(event.contains("code=REMOTE_RECEIPT_MISMATCH"));
        assertFalse(event.contains("another-tenants-operation"));
    }

    @Test void opaqueReferencesStableWithinProcessButDistinctForDifferentInputs() {
        String a=ControlPlaneTelemetry.ref("tenant-x:secret");
        assertEquals(a,ControlPlaneTelemetry.ref("tenant-x:secret"));
        assertNotEquals(a,ControlPlaneTelemetry.ref("tenant-y:secret"));
        assertTrue(a.matches("[0-9a-f]{16}"));
        assertFalse(a.contains("secret"));
    }
}
