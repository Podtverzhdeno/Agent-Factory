package com.agentfactory.control;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import org.junit.jupiter.api.Test;

/** Verifies redacted, after-ack lifecycle publishing telemetry under replay and failure. */
final class LifecycleTelemetryTest {
    private static final String TENANT="confidential-tenant-omega";
    private static final String WORKFLOW="secret-customer-workflow";
    private static final String TRACE="sensitive-trace-id";

    private static InMemoryWorkflowLedger withPendingLifecycle() {
        var ledger=new InMemoryWorkflowLedger();
        var request=new Protocol.Start(TENANT,WORKFLOW,"snapshot","private-idempotency-key",
            new Protocol.Limits(1,new BigDecimal("10"),Instant.parse("2028-01-01T00:00:00Z")),
            TRACE);
        var snapshot=new Protocol.Snapshot(TENANT,"snapshot","READY",
            "sha256:"+"a".repeat(64),"artifact://policies/secret",
            "artifact://datasets/secret","operator","rev-one");
        var workflow=new Workflow(request,snapshot);
        workflow.state=Workflow.State.BUILDING;
        workflow.audit.add(new Workflow.Audit(Instant.parse("2026-10-27T10:00:00Z"),
            Workflow.State.READY,Workflow.State.BUILDING,
            "Bearer private-access-secret",TRACE));
        ledger.open(workflow);
        return ledger;
    }

    private static List<LogRecord> capture(Runnable call) {
        Logger logger=Logger.getLogger(ControlPlaneTelemetry.class.getName());
        Level oldLevel=logger.getLevel();
        boolean oldParent=logger.getUseParentHandlers();
        var records=new ArrayList<LogRecord>();
        Handler handler=new Handler() {
            @Override public void publish(LogRecord record) { records.add(record); }
            @Override public void flush() { }
            @Override public void close() { }
        };
        handler.setLevel(Level.ALL);
        logger.addHandler(handler);
        logger.setLevel(Level.ALL);
        logger.setUseParentHandlers(false);
        try { call.run(); }
        finally {
            logger.removeHandler(handler);
            logger.setLevel(oldLevel);
            logger.setUseParentHandlers(oldParent);
        }
        return List.copyOf(records);
    }

    private static String event(List<LogRecord> records) {
        assertEquals(1,records.size());
        assertNull(records.getFirst().getThrown());
        String message=records.getFirst().getMessage();
        assertTrue(message.startsWith("event=control_plane.lifecycle "));
        assertTrue(message.contains(" from=READY to=BUILDING "));
        assertTrue(message.contains(" sequence=1"));
        assertTrue(message.matches(".* event_ref=[a-f0-9]{16} .*"));
        assertTrue(message.matches(".* workflow_ref=[a-f0-9]{16} .*"));
        assertTrue(message.matches(".* correlation_ref=[a-f0-9]{16} .*"));
        for (String forbidden:List.of(TENANT,WORKFLOW,TRACE,"private-access-secret",
            "Bearer","artifact://","private-idempotency-key")) {
            assertFalse(message.contains(forbidden),"Sensitive lifecycle data leaked");
        }
        return message;
    }

    @Test void publishedLifecycleWritesOneRedactedAckAfterPersistingReceipt() {
        var ledger=withPendingLifecycle();
        var logs=capture(()->{
            assertEquals(1,new LifecycleEventDispatcher(ledger,e->{ }).publishPending());
            assertEquals(0,new LifecycleEventDispatcher(ledger,e->{
                fail("Already published audit event cannot be republished");
            }).publishPending());
        });
        assertTrue(event(logs).contains("outcome=PUBLISHED"));
        assertEquals(Level.INFO,logs.getFirst().getLevel());
        assertEquals(1,ledger.get(TENANT,WORKFLOW).publishedAuditCount);
    }

    @Test void failedPublisherLogsNoExceptionMessageAndDoesNotLoseOutbox() {
        var ledger=withPendingLifecycle();
        var failures=capture(()->{
            IllegalStateException error=assertThrows(IllegalStateException.class,
                ()->new LifecycleEventDispatcher(ledger,e->{
                    throw new IllegalStateException("JWT private-access-secret");
                }).publishPending());
            assertTrue(error.getMessage().contains("private-access-secret"));
        });
        assertTrue(event(failures).contains("outcome=PUBLISH_FAILED"));
        assertEquals(Level.WARNING,failures.getFirst().getLevel());
        assertEquals(0,ledger.get(TENANT,WORKFLOW).publishedAuditCount);
        var next=capture(()->assertEquals(1,
            new LifecycleEventDispatcher(ledger,e->{ }).publishPending()));
        assertTrue(event(next).contains("outcome=PUBLISHED"));
    }

    @Test void latePublisherReceiptIsSupersededWithoutFalseAckLog() {
        var ledger=withPendingLifecycle();
        var logs=capture(()->assertEquals(1,
            new LifecycleEventDispatcher(ledger,e->ledger.transact(TENANT,WORKFLOW,w->{
                w.publishedAuditCount++;
                return null;
            })).publishPending()));
        assertTrue(event(logs).contains("outcome=SUPERSEDED"));
        assertEquals(Level.FINE,logs.getFirst().getLevel());
        assertEquals(1,ledger.get(TENANT,WORKFLOW).publishedAuditCount);
    }

    @Test void loggingNeverExposesDomainAuditReason() {
        var ledger=withPendingLifecycle();
        String msg=event(capture(()->new LifecycleEventDispatcher(ledger,e->{ }).publishPending()));
        assertFalse(msg.contains("Bearer private-access-secret"));
        assertFalse(msg.contains("secret-customer-workflow"));
    }
}
