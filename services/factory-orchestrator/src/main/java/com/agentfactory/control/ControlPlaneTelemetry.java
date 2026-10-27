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
        String safeCode=failureCode!=null && failureCode.matches("[A-Z0-9_]{2,80}")
            ? failureCode : "NONE";
        String message="event=control_plane.outbox"
            +" outcome="+outcome.name()
            +" action="+action.type.name()
            +" workflow_ref="+ref(workflow.tenantId+"\u0000"+workflow.workflowId)
            +" operation_ref="+ref(action.operationId)
            +" correlation_ref="+ref(workflow.correlationId)
            +" attempts="+Math.max(0,Math.min(attempts,5))
            +" code="+safeCode;
        LOGGER.log(level,message);
    }
}
