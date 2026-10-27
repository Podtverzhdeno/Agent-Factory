import pytest

from quality_engine import (
    AccessDenied, Case, Dataset, DatasetVault, EvaluationEngine, EvaluationPolicy,
    EvaluationRequest, InvalidEvidence, ObservedRun, Principal, ToolCall,
    BenchmarkEngine, ModelProfile, ModelRun, BenchmarkPolicy,
)
from gepard_optimizer import OptimizationRequest, OptimizerAdapter, OptimizerInputError


@pytest.fixture
def ev():
    user = Principal("tenant-a", "evaluation")
    vault = DatasetVault()
    cases = (
        Case("rfq-1", {"quotation": [{"sku": "CAS-1", "quantity": 4}]},
             ("catalog.lookup",), ("proof:lookup-1",)),
        Case("cert-1", {"discrepancy": ["expired"]},
             ("certificate.check",), ("proof:certificate-1",)),
    )
    vault.register(user, Dataset("tenant-a", "holdout-v1", "holdout", cases))
    observations = (
        ObservedRun("rfq-1", cases[0].expected_artifact,
                    (ToolCall("catalog.lookup", effect_proof="proof:lookup-1"),),
                    steps=3, latency_ms=120, cost_usd=0.1, graph_events=("tool-call",)),
        ObservedRun("cert-1", cases[1].expected_artifact,
                    (ToolCall("certificate.check", effect_proof="proof:certificate-1"),),
                    steps=4, latency_ms=160, cost_usd=0.05, graph_events=("tool-call",)),
    )
    request = EvaluationRequest("tenant-a", "artifact://spec-v1", "sha256:abc", "holdout-v1",
                                "artifact://policy", "idem-1", "eval-1")
    return user, vault, observations, request


def evaluate(ev, observations=None, request=None):
    user, vault, obs, req = ev
    return EvaluationEngine(vault).evaluate(user, request or req, observations or obs, EvaluationPolicy())


def test_two_distinct_business_cases_pass(ev):
    r = evaluate(ev)
    assert (r.status, r.passed, r.success_rate, r.p95_latency_ms) == ("PASSED", True, 1.0, 160)
    assert r.total_cost_usd == 0.15
    assert r.event("tenant-a", "corr")["passed"]
    assert "quotation" not in str(r.event("tenant-a", "corr"))


def test_plausible_answer_without_tool_action_fails(ev):
    user, vault, obs, req = ev
    bad = ObservedRun("rfq-1", obs[0].artifact, steps=1, graph_events=("final",))
    r = evaluate(ev, (bad, obs[1]))
    assert not r.passed
    assert {f.code for f in r.findings} >= {"REQUIRED_TOOL_MISSING", "VERIFIED_EFFECT_MISSING"}


def test_false_business_document_is_not_passed(ev):
    _, _, obs, _ = ev
    bad = ObservedRun("rfq-1", {"quotation": []}, obs[0].tool_calls, graph_events=("final",))
    assert any(f.code == "BUSINESS_ARTIFACT_MISMATCH" for f in evaluate(ev, (bad, obs[1])).findings)


def test_unauthorized_tool_veto_even_if_business_answer_good(ev):
    _, _, obs, _ = ev
    bad = ObservedRun("rfq-1", obs[0].artifact,
                      obs[0].tool_calls + (ToolCall("payment.charge", approved=False),),
                      graph_events=("tool-call",))
    r = evaluate(ev, (bad, obs[1]))
    assert r.hard_veto and r.status == "FAILED"


def test_memory_policy_violation_is_hard_veto(ev):
    _, _, obs, _ = ev
    bad = ObservedRun("rfq-1", obs[0].artifact, obs[0].tool_calls,
                      memory_violations=("STALE_FACT",), graph_events=("tool-call",))
    assert evaluate(ev, (bad, obs[1])).hard_veto


def test_tool_argument_and_graph_tracing(ev):
    _, _, obs, _ = ev
    bad = ObservedRun("rfq-1", obs[0].artifact,
                      (ToolCall("catalog.lookup", arguments_valid=False, effect_proof="proof:lookup-1"),),
                      steps=26)
    names = {f.code for f in evaluate(ev, (bad, obs[1])).findings}
    assert {"TOOL_ARGUMENT_INVALID", "GRAPH_STEP_LIMIT", "GRAPH_TRACE_MISSING"} <= names


def test_no_cross_tenant_or_optimizer_holdout_access(ev):
    _, vault, _, _ = ev
    with pytest.raises(AccessDenied):
        vault.read(Principal("tenant-b", "evaluation"), "holdout-v1")
    for role in ("optimizer", "builder", "runtime"):
        with pytest.raises(AccessDenied):
            vault.read(Principal("tenant-a", role), "holdout-v1")


def test_optimizer_only_tuning_read():
    vault = DatasetVault()
    p = Principal("a", "evaluation")
    vault.register(p, Dataset("a", "tune-v1", "tune", (Case("c1", {"answer": "a"}),)))
    assert vault.read(Principal("a", "optimizer"), "tune-v1").version == "tune-v1"
    with pytest.raises(AccessDenied):
        vault.read(Principal("a", "builder"), "tune-v1")


def test_duplicate_gold_partition_blocked(ev):
    p, vault, _, _ = ev
    with pytest.raises(InvalidEvidence, match="contamination"):
        vault.register(p, Dataset("tenant-a", "train-v1", "tune",
                                  (Case("other", {"discrepancy": ["expired"]},
                                        ("certificate.check",), ("proof:certificate-1",)),)))


def test_version_is_immutable(ev):
    p, vault, _, _ = ev
    with pytest.raises(InvalidEvidence):
        vault.register(p, vault.read(p, "holdout-v1"))


def test_idempotent_identical_replay(ev):
    user, vault, observations, request = ev
    engine = EvaluationEngine(vault)
    one = engine.evaluate(user, request, observations, EvaluationPolicy())
    two = engine.evaluate(user, request, observations, EvaluationPolicy())
    assert one is two


def test_idempotency_reuse_with_changed_evidence_fails(ev):
    user, vault, obs, request = ev
    engine = EvaluationEngine(vault)
    engine.evaluate(user, request, obs, EvaluationPolicy())
    with pytest.raises(InvalidEvidence, match="idempotency"):
        engine.evaluate(user, request, (ObservedRun("rfq-1", {}, graph_events=("final",)), obs[1]), EvaluationPolicy())


def test_missing_and_duplicate_cases_fail_closed(ev):
    user, vault, obs, request = ev
    for variants in ((obs[0],), (obs[0], obs[0])):
        with pytest.raises(InvalidEvidence):
            EvaluationEngine(vault).evaluate(user, request, variants, EvaluationPolicy())


def test_invalid_principal_and_negative_usage(ev):
    user, vault, obs, req = ev
    with pytest.raises(AccessDenied):
        EvaluationEngine(vault).evaluate(Principal("tenant-b", "evaluation"), req, obs, EvaluationPolicy())
    with pytest.raises(InvalidEvidence):
        evaluate(ev, (ObservedRun("rfq-1", obs[0].artifact, obs[0].tool_calls,
                                  cost_usd=-1, graph_events=("x",)), obs[1]))


def models():
    base = ModelProfile("approved-expensive", True, True, 10000, "EU")
    cheaper = ModelProfile("approved-cheaper", True, True, 10000, "EU")
    baseline = tuple(ModelRun(f"case-{i}", True, False, 0.20, tool_cost_usd=0.03) for i in range(100))
    candidate = tuple(ModelRun(f"case-{i}", True, False, 0.08, tool_cost_usd=0.03) for i in range(100))
    return base, cheaper, baseline, candidate


def test_benchmark_cheaper_verified_noninferior():
    p, c, b, runs = models()
    r = BenchmarkEngine().compare(p, c, b, runs, BenchmarkPolicy())
    assert r.status == "PASSED"
    assert 0 < r.loss_upper_bound < 0.05
    assert r.candidate_cost_per_success < r.baseline_cost_per_success


def test_benchmark_cheap_but_wrong_fails():
    p, c, b, runs = models()
    bad = tuple(ModelRun(r.case_id, i >= 30, False, r.model_cost_usd) for i, r in enumerate(runs))
    r = BenchmarkEngine().compare(p, c, b, bad, BenchmarkPolicy())
    assert r.status == "INCONCLUSIVE"
    assert "QUALITY_NONINFERIORITY_NOT_PROVEN" in r.reasons


def test_benchmark_safety_veto_and_capability():
    p, c, b, runs = models()
    bad = list(runs)
    bad[0] = ModelRun("case-0", True, True, 0.01)
    assert BenchmarkEngine().compare(p, c, b, tuple(bad), BenchmarkPolicy()).status == "FAILED"
    no_tools = ModelProfile("cheap-no-tools", False, True, 10000, "EU")
    assert "MODEL_CAPABILITY_MISMATCH" in BenchmarkEngine().compare(p, no_tools, b, runs, BenchmarkPolicy()).reasons
    other_region = ModelProfile("other-region", True, True, 10000, "US")
    assert BenchmarkEngine().compare(p, other_region, b, runs, BenchmarkPolicy()).status == "FAILED"


def test_benchmark_no_real_savings_after_retries():
    p, c, b, runs = models()
    attempts = tuple(ModelRun(r.case_id, True, False, 0.08, retry_cost_usd=0.20) for r in runs)
    result = BenchmarkEngine().compare(p, c, b, attempts, BenchmarkPolicy())
    assert result.status == "FAILED" and "NO_PROVEN_COST_SAVINGS" in result.reasons


def test_benchmark_small_sample_is_inconclusive():
    p, c, b, runs = models()
    result = BenchmarkEngine().compare(p, c, b[:10], runs[:10], BenchmarkPolicy())
    assert result.status == "INCONCLUSIVE"
    assert "INSUFFICIENT_CASES" in result.reasons


def test_benchmark_misaligned_ids_rejected():
    p, c, b, runs = models()
    bad = (ModelRun("wrong", True, False, 0.01),) + runs[1:]
    with pytest.raises(InvalidEvidence):
        BenchmarkEngine().compare(p, c, b, bad, BenchmarkPolicy())


def test_gepard_adapter_emits_candidate_not_release():
    request = OptimizationRequest("tenant-a", "agent-v1", "agent-v1", "Use catalog tools.",
                                  ("system_prompt",), ("artifact://tune-v1",), ("artifact://validation-v1",))
    o = OptimizerAdapter()
    patch = o.propose(request)
    assert patch.status == "REQUIRES_INDEPENDENT_EVALUATION"
    assert patch.replacement != request.existing_prompt
    assert len(patch.patch_digest) == 64
    assert o.backend_name == "deterministic_mock_not_gepa"


def test_gepard_cannot_use_holdout_or_change_grants():
    base = {"tenant_id": "tenant-a", "agent_spec_ref": "spec-v1", "baseline_spec_ref": "spec-v1",
            "existing_prompt": "P", "allowed_surfaces": ("system_prompt",),
            "tuning_dataset_refs": ("artifact://tune",), "validation_dataset_refs": ("artifact://validation",)}
    for alteration in ({"tuning_dataset_refs": ("artifact://sealed-holdout",)},
                       {"allowed_surfaces": ("tool_permission",)},
                       {"allowed_surfaces": ("system_prompt", "tool_description")}):
        with pytest.raises(OptimizerInputError):
            OptimizerAdapter().propose(OptimizationRequest(**{**base, **alteration}))


def test_gepard_bad_backend_rejected():
    r = OptimizationRequest("tenant-a", "v1", "v1", "Original", ("system_prompt",),
                            ("tune",), ("validation",))
    with pytest.raises(OptimizerInputError):
        OptimizerAdapter(lambda s: s).propose(r)


def test_gepard_deterministic_patch_digest():
    r = OptimizationRequest("tenant-a", "v1", "v1", "Original", ("system_prompt",),
                            ("tune",), ("validation",))
    assert OptimizerAdapter().propose(r).patch_digest == OptimizerAdapter().propose(r).patch_digest
