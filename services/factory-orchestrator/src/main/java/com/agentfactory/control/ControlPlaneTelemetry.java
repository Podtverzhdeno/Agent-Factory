package com.agentfactory.control;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.HexFormat;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Low-cardinality, redacted operational events for the Control Plane.
 *
 * No payloads, bearer tokens, exception messages, artifact references,
 * tenant IDs, user names or raw workflow/operation IDs enter the log.
 * Per-process random salting prevents unsalted dictionary lookup of short IDs.
 * Hashed references remain stable only within a process lifetime; the durable
 * workflow/audit database remains the source of truth across restarts.
 */
public final class ControlPlaneTelemetry {
    private static final Logger LOGGER=Logger.getLogger(ControlPlaneTelemetry.class.getName());
    private static final byte[] SALT=new byte[32];
    static { new SecureRandom().nextBytes(SALT); }

    public enum Outcome {
        ACKNOWLEDGED, SUPERSEDED, RETRY_SCHEDULED, BLOCKED
    }

    public enum NotificationOutcome { PUBLISHED, PUBLISH_FAILED, SUPERSEDED }

    /** Lifecycle notifications are logged after durable ack or failed delivery. */
    static void lifecycle(NotificationOutcome outcome, LifecycleEvent event) {
        Objects.requireNonNull(outcome);Objects.requireNonNull(event);
        Level level=switch(outcome) {
            case PUBLISHED -> Level.INFO;
            case PUBLISH_FAILED -> Level.WARNING;
            case SUPERSEDED -> Level.FINE;
        };
        if(!LOGGER.isLoggable(level)) return;
        String message="event=control_plane.lifecycle"
            +" outcome="+outcome.name()
            +" from="+event.previousState().name()
            +" to="+event.currentState().name()
            +" event_ref="+ref(event.eventId())
            +" workflow_ref="+ref(event.tenantId().length()+":"+event.tenantId()
                +":"+event.workflowId())
            +" correlation_ref="+ref(event.correlationId())
            +" sequence="+Math.max(0,event.sequence());
        LOGGER.log(level,message);
    }

    private ControlPlaneTelemetry() { }

    /** Opaque, process-local reference; never write original identifiers. */
    static String ref(String raw) {
        Objects.requireNonNull(raw);
        try {
            MessageDigest sha=MessageDigest.getInstance("SHA-256");
            sha.update(SALT);
            sha.update(ByteBuffer.allocate(4).putInt(raw.getBytes(StandardCharsets.UTF_8).length).array());
            byte[] digest=sha.digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest,0,8);
        } catch(java.security.NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA256_UNAVAILABLE");
        }
    }

    /** Emits only bounded enums and salted identifiers, not exception detail. */
    static void outbox(Outcome outcome, Workflow workflow, Workflow.Action action,
                       int attempts, String failureCode) {
        Level level=switch(outcome) {
            case BLOCKED -> Level.WARNING;
            case RETRY_SCHEDULED -> Level.INFO;
            case ACKNOWLEDGED -> Level.INFO;
            case SUPERSEDED -> Level.FINE;
        };
        if (!LOGGER.isLoggable(level)) return;
        // An uppercase-looking "error code" may still encode a secret;
        // only known internal diagnostic classifications may appear in logs.
        String safeCode=failureCode==null ? "NONE" : switch(failureCode) {
            case "REMOTE_UNAUTHORIZED", "REMOTE_COMMAND_REJECTED",
                 "REMOTE_RECEIPT_INVALID", "REMOTE_RECEIPT_MISMATCH",
                 "REMOTE_UNAVAILABLE", "OUTBOX_DELIVERY_EXHAUSTED",
                 "SERVICE_AUTH_NOT_CONFIGURED", "REMOTE_DISPATCH_EXCEPTION"
                 -> failureCode;
            default -> "OTHER_FAILURE";
        };
        String message="event=control_plane.outbox"
            +" outcome="+outcome.name()
            +" action="+action.type.name()
            +" workflow_ref="+ref(workflow.tenantId.length()+":"+workflow.tenantId+":"+workflow.workflowId)
            +" operation_ref="+ref(action.operationId)
            +" correlation_ref="+ref(workflow.correlationId)
            +" attempts="+Math.max(0,Math.min(attempts,5))
            +" code="+safeCode;
        LOGGER.log(level,message);
    }
}
