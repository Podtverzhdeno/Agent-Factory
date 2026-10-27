"""Synthetic integration of immutable optimizer proposal and independent Evaluation."""
from quality_engine import (
    Case, Dataset, DatasetVault, EvaluationEngine, EvaluationPolicy,
    EvaluationRequest, ObservedRun, Principal, ToolCall,
)
from gepard_optimizer import OptimizationRequest, OptimizerAdapter


def _mock_runtime(prompt):
    succeeded = "Verify every mandatory tool effect" in prompt
    return ObservedRun(
        "chemical-rfq-01", {"quotation": [{"sku": "C1", "amount": 10}]},
        (ToolCall("catalog.lookup", effect_proof="catalog-audit:fixture-01"),) if succeeded else (),
        graph_events=("tool.call", "tool.result", "final") if succeeded else ("final",),
    )


def test_fail_diagnose_patch_retest_sealed_holdout_without_promotion():
    owner = Principal("test-tenant", "evaluation")
    vault = DatasetVault()
    vault.register(owner, Dataset("test-tenant", "holdout-7", "holdout", (
        Case("chemical-rfq-01", {"quotation": [{"sku": "C1", "amount": 10}]},
             required_tool_calls=("catalog.lookup",),
             required_effect_proofs=("catalog-audit:fixture-01",),
             required_graph_events=("tool.call", "tool.result", "final")),
    )))
    engine = EvaluationEngine(vault)
    prompt = "Create a chemical quotation. Return only the finished answer."
    base = engine.evaluate(owner, EvaluationRequest(
        "test-tenant", "spec-a0", "hash-a0", "holdout-7", "policy-v1", "id-0", "eval-a0"),
        (_mock_runtime(prompt),), EvaluationPolicy())
    assert base.status == "FAILED"
    assert {"REQUIRED_TOOL_MISSING", "VERIFIED_EFFECT_MISSING"} <= {f.code for f in base.findings}

    # GEPARD mock receives tuning/validation references ONLY, never holdout gold.
    patch = OptimizerAdapter().propose(OptimizationRequest(
        "test-tenant", "spec-a0", "spec-a0", prompt, ("system_prompt",),
        ("artifact://tune-v1",), ("artifact://validation-v1",)))
    assert patch.status == "REQUIRES_INDEPENDENT_EVALUATION"
    improved = engine.evaluate(owner, EvaluationRequest(
        "test-tenant", "spec-a1", patch.patch_digest, "holdout-7", "policy-v1", "id-1", "eval-a1"),
        (_mock_runtime(patch.replacement),), EvaluationPolicy())
    assert improved.status == "PASSED" and improved.independent_acceptance
    assert patch.status != "RELEASED"  # Release belongs to the separate control plane.
