package com.agentfactory.control;

import java.time.Instant;

/** Tenant-scoped v0.1 notification with a deterministic replay-safe event ID. */
public record LifecycleEvent(String schemaVersion, String eventId, Instant occurredAt,
                             String tenantId, String workflowId, String correlationId,
                             Workflow.State previousState, Workflow.State currentState,
                             String failureCode, long sequence) { }
