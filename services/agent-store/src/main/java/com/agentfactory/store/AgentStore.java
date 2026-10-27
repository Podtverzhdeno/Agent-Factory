package com.agentfactory.store;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/** Tenant-isolated version catalogue. The deployment/storage boundary is deliberately undecided. */
public interface AgentStore {
    enum Channel { CANDIDATE, VERIFIED, RELEASED, ROLLED_BACK }
    enum Risk { LOW, HIGH }

    record Evidence(String evaluationRunId, String specDigest, String datasetRef,
                    String baselineDigest, String metricsRef, String traceRef,
                    String holdoutEvidenceRef, boolean independent, boolean passed,
                    boolean safetyVeto, boolean effectsVerified, boolean nonRegression,
                    Risk risk, Set<String> approvals) {
        public Evidence { approvals = Set.copyOf(approvals); }
        public boolean complete() {
            return independent && passed && !safetyVeto && effectsVerified && nonRegression &&
                filled(evaluationRunId) && hash(specDigest) && filled(datasetRef) &&
                hash(baselineDigest) && filled(metricsRef) && filled(traceRef) &&
                filled(holdoutEvidenceRef) && risk != null;
        }
    }

    record Version(String tenantId, String agentId, long version, String specRef,
                   String specDigest, Map<String, String> toolDigests, String modelRouteDigest,
                   String a2aCardRef, String rollbackRef, Evidence evidence, Channel channel) {
        public Version {
            toolDigests = Map.copyOf(toolDigests);
            if (version < 1 || !hash(specDigest) || !hash(modelRouteDigest) ||
                toolDigests.isEmpty() || toolDigests.values().stream().anyMatch(d -> !hash(d)) ||
                !filled(specRef) || !specRef.startsWith("artifact://") || !filled(tenantId) ||
                !filled(agentId)) throw new IllegalArgumentException("unpinned version metadata");
        }
        public Version withChannel(Channel channel) {
            return new Version(tenantId, agentId, version, specRef, specDigest, toolDigests,
                modelRouteDigest, a2aCardRef, rollbackRef, evidence, channel);
        }
    }

    record Metadata(String tenantId, String agentId, String specRef, String specDigest,
                    Map<String, String> toolDigests, String modelRouteDigest, String a2aCardRef,
                    Evidence evidence) {
        public Metadata {
            toolDigests = Map.copyOf(toolDigests);
        }
    }

    record Rollback(String rolledBackSpecDigest, Optional<Version> restored) { }

    Version registerCandidate(Metadata metadata, String idempotencyKey);
    Version promote(String tenantId, String agentId, long version, String idempotencyKey,
                    Set<String> approvals, boolean allowLowRiskAuto);
    Rollback rollback(String tenantId, String agentId, long version, String idempotencyKey);
    Optional<Version> active(String tenantId, String agentId);
    List<Version> versions(String tenantId, String agentId);

    static boolean filled(String s) { return s != null && !s.isBlank(); }
    static boolean hash(String s) { return s != null && s.matches("sha256:[0-9a-f]{64}"); }
}
