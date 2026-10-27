package com.agentfactory.control;

import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Privacy-minimised structured operations events.
 *
 * Only internal enums, bounded counters and truncated deterministic hashes
 * reach the log. Never log tokens, tenant IDs, raw correlation/operation IDs,
 * prompts, artifacts, JDBC URLs, exception messages or stack traces.
 *
 * Hashes are pseudonymous, not anonymous: apply access controls and retention.
 */
public final class OperationalLog {
    private static final Logger LOG=Logger.getLogger(OperationalLog.class.getName());
    private OperationalLog() { }

    public enum OutboxOutcome { ACCEPTED, RETRY_SCHEDULED, BLOCKED, STALE_RECEIPT }
    public enum FailureClass {
        NONE, REMOTE_UNAUTHORIZED, REMOTE_COMMAND_REJECTED,
        REMOTE_RECEIPT_INVALID, REMOTE_RECEIPT_MISMATCH,
        REMOTE_UNAVAILABLE, SERVICE_AUTH_NOT_CONFIGURED, OTHER_FAILURE
    }
    public enum NotificationOutcome { PUBLISHED, PUBLISH_FAILED }

    static String reference(String raw) {
        // Hash the entire value, never include user-controlled raw content.
        return raw == null ? "missing" : EventIdentity.sha256(raw).substring(0,16);
    }
    public static FailureClass failureClass(RuntimeException error) {
        Objects.requireNonNull(error);
        String code=error.getMessage();
        if(error instanceof Protocol.RemoteCommandFailure ||
           error instanceof IllegalStateException) {
            if("REMOTE_UNAUTHORIZED".equals(code)) return FailureClass.REMOTE_UNAUTHORIZED;
            if("REMOTE_COMMAND_REJECTED".equals(code)) return FailureClass.REMOTE_COMMAND_REJECTED;
            if("REMOTE_RECEIPT_INVALID".equals(code)) return FailureClass.REMOTE_RECEIPT_INVALID;
            if("REMOTE_RECEIPT_MISMATCH".equals(code)) return FailureClass.REMOTE_RECEIPT_MISMATCH;
            if("REMOTE_UNAVAILABLE".equals(code)) return FailureClass.REMOTE_UNAVAILABLE;
            if("SERVICE_AUTH_NOT_CONFIGURED".equals(code))
                return FailureClass.SERVICE_AUTH_NOT_CONFIGURED;
        }
        return FailureClass.OTHER_FAILURE;
    }
    public static void outbox(Workflow w,Workflow.Action action,OutboxOutcome outcome,
                              int attempt,FailureClass reason) {
        Objects.requireNonNull(w);Objects.requireNonNull(action);
        Objects.requireNonNull(outcome);Objects.requireNonNull(reason);
        Level level=outcome==OutboxOutcome.BLOCKED ? Level.WARNING : Level.INFO;
        if(!LOG.isLoggable(level)) return;
        LOG.log(level,"event=control.outbox"
            +" tenant_ref="+reference(w.tenantId)
            +" workflow_ref="+reference(w.workflowId)
            +" operation_ref="+reference(action.operationId)
            +" action="+action.type.name()
            +" outcome="+outcome.name()
            +" attempt="+Math.max(0,Math.min(attempt,5))
            +" failure_class="+reason.name());
    }
    public static void notification(LifecycleEvent event,NotificationOutcome outcome) {
        Objects.requireNonNull(event);Objects.requireNonNull(outcome);
        Level level=outcome==NotificationOutcome.PUBLISH_FAILED ? Level.WARNING : Level.INFO;
        if(!LOG.isLoggable(level)) return;
        LOG.log(level,"event=control.lifecycle"
            +" tenant_ref="+reference(event.tenantId())
            +" workflow_ref="+reference(event.workflowId())
            +" event_ref="+reference(event.eventId())
            +" from="+event.previousState().name()
            +" to="+event.currentState().name()
            +" sequence="+event.sequence()
            +" outcome="+outcome.name());
    }
}
