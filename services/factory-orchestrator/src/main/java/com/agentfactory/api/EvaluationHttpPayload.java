package com.agentfactory.api;

import com.agentfactory.control.Protocol;
import java.util.Map;
import java.util.Objects;

/** Strict v0.1 wire payload accepted by workstream 05's EvaluationRequestBody. */
public final class EvaluationHttpPayload {
    private EvaluationHttpPayload() { }

    public static Map<String, String> from(Protocol.EvaluationCommand command) {
        Objects.requireNonNull(command, "command");
        // Keep exactly the fields accepted by Evaluation's Pydantic extra=forbid model.
        // correlation_id is a trace header; baseline_spec_digest is internal.
        return Map.of(
            "tenant_id", command.tenantId(),
            "agent_spec_ref", command.specRef(),
            "agent_spec_digest", command.specDigest(),
            "dataset_version_ref", command.datasetRef(),
            "policy_ref", command.policyRef(),
            "idempotency_key", command.idempotencyKey(),
            "evaluation_run_id", command.operationId());
    }
}
