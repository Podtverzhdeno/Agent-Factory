package com.agentfactory.control;

import com.agentfactory.store.AgentStore;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;

/** Local aggregate. All mutations require a WorkflowLedger transaction. */
public final class Workflow {
    public enum State { DRAFT, READY, BUILDING, TESTING, OPTIMIZING, TRAINING, RE_TESTING, VERIFIED, BLOCKED, RELEASED, ROLLED_BACK }
    public enum ActionType { BUILD, EVALUATE, OPTIMIZE, SOUP }

    public record Audit(Instant occurredAt, State from, State to, String reason, String correlationId) { }
    List<Audit> audit = new ArrayList<>();
    long candidateVersion;

    public static final class Action {
        String operationId;
        ActionType type;
        String specRef;
        String specDigest;
        String idempotencyKey;
        boolean delivered;
        int attempts;
        String lastError;
        public Action() { }
        Action(String id, ActionType type, String ref, String digest) {
            this.operationId = id; this.type = type; this.specRef = ref; this.specDigest = digest;
            this.idempotencyKey = "control:" + id;
        }
        Action copy() {
            Action a = new Action(operationId, type, specRef, specDigest);
            a.delivered = delivered; a.attempts = attempts; a.lastError = lastError;
            return a;
        }
    }

    String tenantId;
    String workflowId;
    String idempotencyKey;
    RequestIdentity requestFingerprint;
    record RequestIdentity(String tenantId, String workflowId, String taskSnapshotId,
                           Protocol.Limits limits) { }
    String taskSnapshotId;
    String snapshotDigest;
    String snapshotRevision;
    String datasetRef;
    String policyRef;
    String correlationId;
    Protocol.Limits limits;
    State state = State.DRAFT;
    Instant startedAt;
    BigDecimal spentUsd = BigDecimal.ZERO;
    int repairs;
    int trainingAttempts;
    String trainingIdempotencyKey;
    String trainingRightsRef;
    String agentId;
    String specRef;
    String specDigest;
    String baselineRef;
    String baselineDigest;
    Map<String, String> toolDigests = new HashMap<>();
    String modelRouteDigest;
    String a2aCardRef;
    String pendingOperationId;
    AgentStore.Evidence lastEvidence;
    long releasedVersion;
    String errorCode;
    String requiredAction;
    List<Action> actions = new ArrayList<>();
    Map<String, String> inbox = new HashMap<>();
    long revision;

    public Workflow() { }
    Workflow(Protocol.Start req, Protocol.Snapshot snapshot) {
        tenantId = req.tenantId(); workflowId = req.workflowId(); idempotencyKey = req.idempotencyKey();
        requestFingerprint = fingerprint(req); taskSnapshotId = req.taskSnapshotId();
        snapshotDigest = snapshot.digest(); snapshotRevision = snapshot.snapshotRevision();
        datasetRef = snapshot.datasetVersionRef(); policyRef = snapshot.evaluationPolicyRef();
        correlationId = req.correlationId(); limits = req.limits(); startedAt = Instant.now();
    }
    static RequestIdentity fingerprint(Protocol.Start r) {
        return new RequestIdentity(r.tenantId(), r.workflowId(), r.taskSnapshotId(), r.limits());
    }
    Workflow copy() {
        Workflow w = new Workflow();
        w.tenantId=tenantId; w.workflowId=workflowId; w.idempotencyKey=idempotencyKey;
        w.requestFingerprint=requestFingerprint; w.taskSnapshotId=taskSnapshotId; w.snapshotDigest=snapshotDigest;
        w.snapshotRevision=snapshotRevision; w.datasetRef=datasetRef; w.policyRef=policyRef;
        w.correlationId=correlationId; w.limits=limits; w.state=state; w.startedAt=startedAt;
        w.spentUsd=spentUsd; w.repairs=repairs; w.trainingAttempts=trainingAttempts;
        w.trainingIdempotencyKey=trainingIdempotencyKey; w.trainingRightsRef=trainingRightsRef;
        w.agentId=agentId; w.specRef=specRef; w.specDigest=specDigest;
        w.baselineRef=baselineRef; w.baselineDigest=baselineDigest;
        w.toolDigests=new HashMap<>(toolDigests); w.modelRouteDigest=modelRouteDigest;
        w.a2aCardRef=a2aCardRef; w.pendingOperationId=pendingOperationId;
        w.lastEvidence=lastEvidence; w.releasedVersion=releasedVersion;
        w.errorCode=errorCode; w.requiredAction=requiredAction;
        for (Action action: actions) w.actions.add(action.copy());
        w.inbox=new HashMap<>(inbox); w.revision=revision;
        w.audit=new ArrayList<>(audit); w.candidateVersion=candidateVersion;
        return w;
    }
    String enqueue(ActionType type, String specRef, String digest) {
        String id = workflowId + ":" + type.name().toLowerCase(Locale.ROOT) + ":" + (actions.size() + 1);
        actions.add(new Action(id, type, specRef, digest));
        pendingOperationId = id;
        return id;
    }
    boolean hasPendingActions() {
        return actions.stream().anyMatch(a -> !a.delivered && a.attempts < 5
            && a.operationId.equals(pendingOperationId) && actionAllowed(a.type));
    }
    boolean actionAllowed(ActionType type) {
        return switch (type) {
            case BUILD -> state == State.BUILDING;
            case EVALUATE -> state == State.TESTING || state == State.RE_TESTING;
            case OPTIMIZE -> state == State.OPTIMIZING;
            case SOUP -> state == State.TRAINING;
        };
    }
    public View view() {
        return new View(tenantId, workflowId, taskSnapshotId, state, agentId, specRef, specDigest,
            repairs, trainingAttempts, spentUsd, candidateVersion, releasedVersion, pendingOperationId, errorCode,
            requiredAction, revision);
    }
    public record View(String tenantId, String workflowId, String taskSnapshotId, State state,
                       String agentId, String specRef, String specDigest, int repairs, int trainingAttempts,
                       BigDecimal spentUsd, long candidateVersion, long releasedVersion, String pendingOperationId,
                       String errorCode, String requiredAction, long revision) { }
}
