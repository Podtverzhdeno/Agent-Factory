package com.agentfactory.control;

import com.agentfactory.store.AgentStore;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

/** Proposed v0.1 transport-neutral, tenant-bound command/event payloads. */
public final class Protocol {
    private Protocol() { }
    public record Principal(String subject, String tenantId, java.util.Set<String> scopes) {
        public Principal { scopes = java.util.Set.copyOf(scopes); }
    }
    public record Limits(int maxRepairs, BigDecimal maxUsd, Instant deadline) {
        public Limits {
            if (maxRepairs < 0 || maxRepairs > 10 || maxUsd == null || maxUsd.signum() <= 0 || deadline == null)
                throw new IllegalArgumentException("INVALID_LIMITS");
        }
    }
    public record Start(String tenantId, String workflowId, String taskSnapshotId,
                        String idempotencyKey, Limits limits, String correlationId) { }
    public record Snapshot(String tenantId, String taskSnapshotId, String status,
                           String digest, String evaluationPolicyRef, String datasetVersionRef,
                           String createdBy, String snapshotRevision) { }
    public record Header(String schemaVersion, String eventId, String tenantId, String workflowId,
                         String operationId, String correlationId, Instant occurredAt) { }
    public record BuildFinished(Header header, boolean success, String agentId,
                                String specRef, String specDigest, Map<String,String> toolDigests,
                                String modelRouteDigest, String a2aCardRef,
                                String failureCode, boolean retryable) { }
    public record EvaluationFinished(Header header, String evaluationRunId, String specDigest,
                                     AgentStore.Evidence evidence, BigDecimal spendUsd,
                                     String failureCode, boolean retryable) { }
    public record OptimizationFinished(Header header, boolean success, String baseSpecDigest,
                                       String candidateSpecRef, String candidateSpecDigest,
                                       BigDecimal spendUsd, String failureCode, boolean retryable) { }
    public record SoupFinished(Header header, boolean success, String baseSpecDigest,
                               String candidateSpecRef, String candidateSpecDigest,
                               String modelRouteDigest, BigDecimal spendUsd,
                               String failureCode, boolean retryable) { }
    public record CommandReceipt(String operationId, boolean accepted) { }
    public record BuildCommand(String tenantId, String workflowId, String taskSnapshotId,
                               String snapshotDigest, String operationId, String idempotencyKey,
                               String correlationId, String policyRef) { }
    public record EvaluationCommand(String tenantId, String workflowId, String operationId,
                                    String specRef, String specDigest, String baselineDigest,
                                    String datasetRef, String policyRef, String idempotencyKey,
                                    String correlationId) { }
    public record OptimizationCommand(String tenantId, String workflowId, String operationId,
                                      String specRef, String specDigest, String baselineSpecRef,
                                      String baselineDigest, String datasetRef,
                                      String allowedSurfaces, String idempotencyKey,
                                      String correlationId) { }
    public record SoupCommand(String tenantId, String workflowId, String operationId,
                              String specRef, String baselineDigest, String rightsRef,
                              String idempotencyKey, String correlationId) { }
}
