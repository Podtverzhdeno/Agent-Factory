package com.agentfactory.control;

import java.util.List;
import java.util.Optional;
import java.util.function.Function;

public final class Ports {
    private Ports() { }
    public interface TaskSnapshotReader {
        Protocol.Snapshot readReady(String tenant, String snapshotId);
    }
    public interface BuildClient { Protocol.CommandReceipt submit(Protocol.BuildCommand command); }
    public interface EvaluationClient { Protocol.CommandReceipt submit(Protocol.EvaluationCommand command); }
    public interface OptimizationClient { Protocol.CommandReceipt submit(Protocol.OptimizationCommand command); }
    public interface SoupClient { Protocol.CommandReceipt submit(Protocol.SoupCommand command); }
    public interface TenantAuthz { void check(Protocol.Principal actor, String tenant, String scope); }
    /** Validate provenance from an evaluator-owned source rather than trusting an event field. */
    public interface EvidenceVerifier {
        void validate(String tenant, String evaluationRunId, String specDigest,
                      com.agentfactory.store.AgentStore.Evidence evidence);
    }
    public interface ApprovalReader { boolean approved(String tenant, String workflow, String purpose); }
    public interface ReleasePolicy { boolean allowAutomaticLowRisk(Workflow.View workflow); }
    public interface TimeSource { java.time.Instant now(); }
    public interface OutboxPublisher { void publish(LifecycleEvent event); }
    public record Key(String tenantId, String workflowId) { }
    public interface WorkflowLedger {
        Workflow open(Workflow initial);
        Optional<Workflow> byIdempotency(String tenant, String key);
        Workflow get(String tenant, String workflowId);
        <T> T transact(String tenant, String workflowId, Function<Workflow,T> operation);
        List<Key> withUndeliveredActions();
        List<Key> activeKeys();
        List<Key> withUndeliveredEvents();
    }
}
