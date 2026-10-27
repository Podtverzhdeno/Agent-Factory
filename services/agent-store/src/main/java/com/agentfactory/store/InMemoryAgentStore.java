package com.agentfactory.store;

import java.util.*;

/** Deterministic mock-backed adapter; not a durable production repository. */
public final class InMemoryAgentStore implements AgentStore {
    private record AgentKey(String tenantId, String agentId) { }
    private record OperationKey(String tenantId, String kind, String idempotencyKey) { }
    private final Map<AgentKey, List<Version>> catalogue = new HashMap<>();
    private final Map<OperationKey, Object> operationFingerprints = new HashMap<>();
    private final Map<OperationKey, Version> operationVersions = new HashMap<>();
    private final Map<OperationKey, Rollback> rollbacks = new HashMap<>();
    private final Map<AgentKey, List<Transition>> transitions = new HashMap<>();
    private void record(String tenant, String agent, long version, Channel from, Channel to,
                        String operation, String evaluationRun, Set<String> approvals) {
        transitions.computeIfAbsent(key(tenant,agent), ignored -> new ArrayList<>())
            .add(new Transition(version,from,to,operation,evaluationRun,approvals));
    }

    private static AgentKey key(String tenant, String agent) { return new AgentKey(tenant, agent); }
    private static OperationKey op(String tenant, String kind, String operation) {
        return new OperationKey(tenant, kind, operation);
    }
    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }

    @Override public synchronized Version registerCandidate(Metadata m, String key) {
        Objects.requireNonNull(m, "metadata");
        Objects.requireNonNull(key, "idempotencyKey");
        OperationKey op = op(m.tenantId(), "candidate", key);
        Metadata fingerprint = m;
        if (operationVersions.containsKey(op)) {
            require(Objects.equals(operationFingerprints.get(op), fingerprint), "IDEMPOTENCY_CONFLICT");
            return operationVersions.get(op);
        }
        require(m.evidence() != null && m.evidence().complete(), "INCOMPLETE_EVIDENCE");
        require(m.specDigest().equals(m.evidence().specDigest()), "SPEC_DIGEST_MISMATCH");
        List<Version> list = catalogue.computeIfAbsent(key(m.tenantId(), m.agentId()), ignored -> new ArrayList<>());
        Version v = new Version(m.tenantId(), m.agentId(), list.size() + 1L, m.specRef(),
            m.specDigest(), m.toolDigests(), m.modelRouteDigest(), m.a2aCardRef(),
            null, m.evidence(), Channel.VERIFIED);
        list.add(v);
        record(m.tenantId(),m.agentId(),v.version(),Channel.CANDIDATE,Channel.VERIFIED,
            key,m.evidence().evaluationRunId(),Set.of());
        operationFingerprints.put(op, fingerprint);
        operationVersions.put(op, v);
        return v;
    }

    @Override public synchronized Version promote(String tenant, String agent, long version,
                                                   String operation, Set<String> approvals, boolean auto) {
        Objects.requireNonNull(approvals, "approvals");
        OperationKey op = op(tenant, "promote", operation);
        Object fp = List.of(agent, version, auto, Set.copyOf(approvals));
        if (operationVersions.containsKey(op)) {
            require(Objects.equals(operationFingerprints.get(op), fp), "IDEMPOTENCY_CONFLICT");
            return operationVersions.get(op);
        }
        List<Version> list = catalogue.get(key(tenant, agent));
        require(list != null && version >= 1 && version <= list.size(), "VERSION_NOT_FOUND");
        Version candidate = list.get((int)version - 1);
        require(candidate.channel() == Channel.VERIFIED, "VERSION_NOT_VERIFIED");
        require(candidate.evidence().complete(), "QUALITY_GATE_BLOCKED");
        require(auto ? (candidate.evidence().risk() == Risk.LOW && approvals.isEmpty())
                     : approvals.contains("release:approve"),
            "HUMAN_APPROVAL_REQUIRED");
        String rollbackRef = active(tenant, agent).map(v -> "agentstore://" + tenant + "/" + agent + "/" + v.version()).orElse(null);
        for (int i = 0; i < list.size(); i++) {
            Version prior = list.get(i);
            if (prior.channel() == Channel.RELEASED) {
                list.set(i, prior.withChannel(Channel.VERIFIED));
                record(tenant,agent,prior.version(),Channel.RELEASED,Channel.VERIFIED,
                    operation,prior.evidence().evaluationRunId(),Set.of());
            }
        }
        Version released = new Version(candidate.tenantId(), candidate.agentId(), candidate.version(),
            candidate.specRef(), candidate.specDigest(), candidate.toolDigests(), candidate.modelRouteDigest(),
            candidate.a2aCardRef(), rollbackRef, candidate.evidence(), Channel.RELEASED);
        list.set((int)version - 1, released);
        record(tenant,agent,version,Channel.VERIFIED,Channel.RELEASED,
            operation,candidate.evidence().evaluationRunId(),approvals);
        operationFingerprints.put(op, fp);
        operationVersions.put(op, released);
        return released;
    }

    @Override public synchronized Rollback rollback(String tenant, String agent, long version, String operation) {
        OperationKey op = op(tenant, "rollback", operation);
        Object fp = List.of(agent, version);
        if (rollbacks.containsKey(op)) {
            require(Objects.equals(operationFingerprints.get(op), fp), "IDEMPOTENCY_CONFLICT");
            return rollbacks.get(op);
        }
        List<Version> list = catalogue.get(key(tenant, agent));
        require(list != null && version >= 1 && version <= list.size(), "VERSION_NOT_FOUND");
        Version target = list.get((int)version - 1);
        require(target.channel() == Channel.RELEASED, "VERSION_NOT_ACTIVE");
        Optional<Version> restored = Optional.empty();
        if (target.rollbackRef() != null) {
            long older = Long.parseLong(target.rollbackRef().substring(target.rollbackRef().lastIndexOf('/') + 1));
            Version previous = list.get((int)older - 1);
            require(previous.channel() == Channel.VERIFIED, "ROLLBACK_TARGET_NOT_VERIFIED");
            Version active = previous.withChannel(Channel.RELEASED);
            list.set((int)older - 1, active);
            record(tenant,agent,older,Channel.VERIFIED,Channel.RELEASED,
                operation,previous.evidence().evaluationRunId(),Set.of());
            restored = Optional.of(active);
        }
        list.set((int)version - 1, target.withChannel(Channel.ROLLED_BACK));
        record(tenant,agent,version,Channel.RELEASED,Channel.ROLLED_BACK,
            operation,target.evidence().evaluationRunId(),Set.of());
        Rollback result = new Rollback(target.specDigest(), restored);
        operationFingerprints.put(op, fp);
        rollbacks.put(op, result);
        return result;
    }

    @Override public synchronized Optional<Version> active(String tenant, String agent) {
        return catalogue.getOrDefault(key(tenant, agent), List.of()).stream()
            .filter(v -> v.channel() == Channel.RELEASED).findFirst();
    }
    @Override public synchronized List<Transition> history(String tenant, String agent) {
        return List.copyOf(transitions.getOrDefault(key(tenant,agent),List.of()));
    }
    @Override public synchronized List<Version> versions(String tenant, String agent) {
        return List.copyOf(catalogue.getOrDefault(key(tenant, agent), List.of()));
    }
}
