package com.agentfactory.control;

import java.util.*;
import java.util.function.Function;

/** Atomic workflow state, event inbox and command outbox for isolated component tests. */
public final class InMemoryWorkflowLedger implements Ports.WorkflowLedger {
    private final Map<Ports.Key, Workflow> workflows = new HashMap<>();
    private record IdempotencyKey(String tenantId, String clientKey) { }
    private final Map<IdempotencyKey, Ports.Key> idem = new HashMap<>();
    private static IdempotencyKey idemKey(String tenant, String key) {
        return new IdempotencyKey(tenant, key);
    }

    @Override public synchronized Workflow open(Workflow initial) {
        IdempotencyKey k = idemKey(initial.tenantId, initial.idempotencyKey);
        Ports.Key id = new Ports.Key(initial.tenantId, initial.workflowId);
        Ports.Key previous = idem.get(k);
        if (previous != null) {
            Workflow saved = workflows.get(previous);
            if (!saved.requestFingerprint.equals(initial.requestFingerprint)) throw new IllegalStateException("IDEMPOTENCY_CONFLICT");
            return saved.copy();
        }
        if (workflows.containsKey(id)) throw new IllegalStateException("WORKFLOW_ALREADY_EXISTS");
        Workflow copy = initial.copy();
        workflows.put(id, copy);
        idem.put(k,id);
        return copy.copy();
    }
    @Override public synchronized Optional<Workflow> byIdempotency(String tenant, String key) {
        Ports.Key k = idem.get(idemKey(tenant,key));
        return k == null ? Optional.empty() : Optional.of(workflows.get(k).copy());
    }
    @Override public synchronized Workflow get(String tenant, String workflow) {
        Workflow found = workflows.get(new Ports.Key(tenant,workflow));
        if (found == null) throw new NoSuchElementException("WORKFLOW_NOT_FOUND");
        return found.copy();
    }
    @Override public synchronized <T> T transact(String tenant, String id, Function<Workflow,T> transaction) {
        Ports.Key key = new Ports.Key(tenant,id);
        Workflow found = workflows.get(key);
        if (found == null) throw new NoSuchElementException("WORKFLOW_NOT_FOUND");
        Workflow working = found.copy();
        // A transaction's response must reflect the revision that will be committed.
        working.revision++;
        T result = transaction.apply(working);
        if (found.state != working.state) working.audit.add(new Workflow.Audit(java.time.Instant.now(),
            found.state, working.state, working.errorCode, working.correlationId));
        workflows.put(key, working);
        return result;
    }
    @Override public synchronized List<Ports.Key> activeKeys() {
        return workflows.entrySet().stream().filter(e ->
            e.getValue().state!=Workflow.State.BLOCKED &&
            e.getValue().state!=Workflow.State.RELEASED &&
            e.getValue().state!=Workflow.State.ROLLED_BACK)
            .map(Map.Entry::getKey).toList();
    }
    @Override public synchronized List<Ports.Key> withUndeliveredEvents() {
        return workflows.entrySet().stream().filter(e ->
            e.getValue().publishedAuditCount < e.getValue().audit.size())
            .map(Map.Entry::getKey).toList();
    }
    @Override public synchronized List<Ports.Key> withUndeliveredActions() {
        return workflows.entrySet().stream().filter(e -> e.getValue().hasPendingActions())
            .map(Map.Entry::getKey).toList();
    }
}
