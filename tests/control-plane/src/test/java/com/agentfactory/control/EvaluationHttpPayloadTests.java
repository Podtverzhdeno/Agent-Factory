package com.agentfactory.control;

import com.agentfactory.api.EvaluationHttpPayload;
import java.util.Map;
import java.util.Set;

/** Current Evaluation branch strict Pydantic input contract, dependency-free Java proof. */
public final class EvaluationHttpPayloadTests {
    private EvaluationHttpPayloadTests() { }
    private static void check(boolean ok) {
        if (!ok) throw new AssertionError("EVALUATION_HTTP_CONTRACT_MISMATCH");
    }
    public static void main(String[] ignored) {
        var command = new Protocol.EvaluationCommand(
            "tenant-a", "workflow-1", "workflow-1:evaluate:2",
            "artifact://agent-specs/a1", "sha256:" + "a".repeat(64),
            "sha256:" + "b".repeat(64), "artifact://datasets/v1",
            "artifact://policies/acceptance-v1", "control:workflow-1:evaluate:2", "trace-1");
        Map<String,String> body=EvaluationHttpPayload.from(command);
        check(body.keySet().equals(Set.of("tenant_id", "agent_spec_ref",
            "agent_spec_digest", "dataset_version_ref", "policy_ref",
            "idempotency_key", "evaluation_run_id")));
        check(body.get("evaluation_run_id").equals(command.operationId()));
        check(body.get("tenant_id").equals(command.tenantId()));
        check(body.get("agent_spec_digest").equals(command.specDigest()));
        check(body.get("idempotency_key").equals(command.idempotencyKey()));
        check(!body.containsKey("operation_id") && !body.containsKey("schema_version") &&
            !body.containsKey("baseline_spec_digest") && !body.containsKey("correlation_id"));
        System.out.println("EVALUATION HTTP CONTRACT TESTS PASSED: 5");
    }
}
