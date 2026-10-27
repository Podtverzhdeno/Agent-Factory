package com.agentfactory.store;

import java.util.*;

/** Deterministic mock-backed adapter; not a durable production repository. */
public final class InMemoryAgentStore implements AgentStore {
    private final Map<String, List<Version>> catalogue = new HashMap<>();
    private final Map<String, String> operationFingerprints = new HashMap<>();
    private final Map<String, Version> operationVersions = new HashMap<>();
    private final Map<String, Rollback> rollbacks = new HashMap<>();

    private static String key(String tenant, String agent) { return tenant + "\u001f" + agent; }
    private static String op(String tenant, String operation) { return tenant + "\u001f" + operation; }
    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }

    @Override public synchronized Version registerCandidate(Metadata m, String key) {
        String op = op(m.tenantId(), key);
        String fingerprint = m.agentId() + ":" + m.specDigest() + ":" + m.specRef();
        if (operationVersions.containsKey(op)) {
            require(operationFingerprints.get(op).equals(fingerprint), "IDEMPOTENCY_CONFLICT");
            return operationVersions.get(op);
        }
        require(m.evidence() != null && m.evidence().complete(), "INCOMPLETE_EVIDENCE");
        require(m.specDigest().equals(m.evidence().specDigest()), "SPEC_DIGEST_MISMATCH");
        List<Version> list = catalogue.computeIfAbsent(key(m.tenantId(), m.agentId()), ignored -> new ArrayList<>());
        Version v = new Version(m.tenantId(), m.agentId(), list.size() + 1L, m.specRef(),
            m.specDigest(), m.toolDigests(), m.modelRouteDigest(), m.a2aCardRef(),
            null, m.evidence(), Channel.VERIFIED);
        list.add(v);
        operationFingerprints.put(op, fingerprint);
        operationVersions.put(op, v);
        return v;
    }

    @Override public synchronized Version promote(String tenant, String agent, long version,
                                                   String operation, Set<String> approvals, boolean auto) {
        String op = op(tenant, operation);
        String fp = agent + ":" + version + ":" + auto;
        if (operationVersions.containsKey(op)) {
            require(operationFingerprints.get(op).equals(fp), "IDEMPOTENCY_CONFLICT");
            return operationVersions.get(op);
        }
        List<Version> list = catalogue.get(key(tenant, agent));
        require(list != null && version >= 1 && version <= list.size(), "VERSION_NOT_FOUND");
        Version candidate = list.get((int)version - 1);
        require(candidate.channel() == Channel.VERIFIED, "VERSION_NOT_VERIFIED");
        require(candidate.evidence().complete(), "QUALITY_GATE_BLOCKED");
        require(candidate.evidence().risk() == Risk.LOW && auto || approvals.contains("release:approve"),
            "HUMAN_APPROVAL_REQUIRED");
        String rollbackRef = active(tenant, agent).map(v -> "agentstore://" + tenant + "/" + agent + "/" + v.version()).orElse(null);
        for (int i = 0; i < list.size(); i++) {
            Version prior = list.get(i);
            if (prior.channel() == Channel.RELEASED) list.set(i, prior.withChannel(Channel.VERIFIED));
        }
        Version released = new Version(candidate.tenantId(), candidate.agentId(), candidate.version(),
            candidate.specRef(), candidate.specDigest(), candidate.toolDigests(), candidate.modelRouteDigest(),
            candidate.a2aCardRef(), rollbackRef, candidate.evidence(), Channel.RELEASED);
        list.set((int)version - 1, released);
        operationFingerprints.put(op, fp);
        operationVersions.put(op, released);
        return released;
    }

    @Override public synchronized Rollback rollback(String tenant, String agent, long version, String operation) {
        String op = op(tenant, operation);
        String fp = agent + ":" + version;
        if (rollbacks.containsKey(op)) {
            require(operationFingerprints.get(op).equals(fp), "IDEMPOTENCY_CONFLICT");
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
            restored = Optional.of(active);
        }
        list.set((int)version - 1, target.withChannel(Channel.ROLLED_BACK));
        Rollback result = new Rollback(target.specDigest(), restored);
        operationFingerprints.put(op, fp);
        rollbacks.put(op, result);
        return result;
    }

    @Override public synchronized Optional<Version> active(String tenant, String agent) {
        return catalogue.getOrDefault(key(tenant, agent), List.of()).stream()
            .filter(v -> v.channel() == Channel.RELEASED).findFirst();
    }
    @Override public synchronized List<Version> versions(String tenant, String agent) {
        return List.copyOf(catalogue.getOrDefault(key(tenant, agent), List.of()));
    }
}
