"""Real Agent04 Python Runtime -> Ed25519 HTTP -> Agent05 Quality tests.

Both workstreams are copied without modifying main. This executes the real
producer, parser, verifier, SQLite evaluation workflow and outbox; the model
and business tool are controlled synthetic fixtures. GEPARD below is its
deterministic backend, NOT a production DSPy optimization. Release requires
the independent Java Control Plane and is not asserted here.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
for name in ("agent-builder", "agent-runtime"):
    sys.path.insert(0, str(ROOT / "services" / name))
sys.path.insert(0, str(ROOT / "services" / "evaluation"))
sys.path.insert(0, str(ROOT / "services" / "gepard-optimizer"))
sys.path.insert(0, str(ROOT / "tests" / "agent-engine"))

from agent_builder import digest  # noqa: E402
from agent_runtime import Decision, EffectLedger, Runtime, ToolPolicy  # noqa: E402
from agent_runtime.evaluation_audit import (  # noqa: E402
    EvidenceRecordingGateway, RuntimeAuditReadAPI, SignedRuntimeAudit,
)
from gepard_optimizer.core import OptimizationRequest, OptimizerAdapter  # noqa: E402
from quality_engine.core import (  # noqa: E402
    Case, Dataset, DatasetVault, EvaluationRequest, Principal,
)
from quality_engine.durable_workflow import DurableEvaluationWorkflow  # noqa: E402
from quality_engine.ed25519_audit import Ed25519EvidenceVerifier, RuntimeAuditPublicKey  # noqa: E402
from quality_engine.runtime_http import RuntimeEvidenceHTTPCollector  # noqa: E402
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata  # noqa: E402
from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task  # noqa: E402


def _agent(*, uses_tool: bool, candidate_spec=None):
    spec = candidate_spec or build(
        task("rfq", ["draft"], ["draft_file"], ["draft:write"]),
        Registry([manifest("quote.render", ["draft"], ["draft_file"], ["draft:write"])]),
    )
    binding = spec.selected_tools[0]
    policies = {binding.tool_id: ToolPolicy(
        tenant_id=spec.tenant_id,
        tool_id=binding.tool_id,
        version=binding.version,
        manifest_digest=binding.digest,
        scopes=frozenset(binding.granted_scopes),
        effect_mode="draft_file", input_schema={"type": "object"},
        output_schema={"type": "object"},
    )}
    actions = ([Decision(kind="tool", tool_id=binding.tool_id, args={}),
                Decision(kind="final", text="Quotation drafted")]
               if uses_tool else [Decision(kind="final", text="Quotation drafted")])
    tools = FakeTools()
    gateway = EvidenceRecordingGateway(tools, EffectLedger(), policies=policies)
    runtime = Runtime(ScriptedModel(actions), gateway,
                      approved_spec_digests=frozenset({spec.artifact_digest}))
    private = Ed25519PrivateKey.generate()
    audit = SignedRuntimeAudit(runtime, spec, private_key=private, key_id="runtime-v1")
    return spec, tools, private, audit


def _collect_and_evaluate(tmp_path, spec, private, audit, *, eval_id: str,
                          expected_tool: bool, corrupt: bool = False):
    token = "synthetic-service-token"
    api = RuntimeAuditReadAPI(
        audit, authenticate=lambda given: "buyer" if given == token else None)
    requests = []

    def transport_handler(request):
        requests.append(request)
        async def forward():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api),
                base_url="http://127.0.0.1:8010",
            ) as async_client:
                reply = await async_client.request(
                    request.method, str(request.url),
                    headers=dict(request.headers), content=request.content,
                )
                if corrupt and reply.status_code == 200:
                    payload = reply.json()
                    payload["envelope"]["observation"]["artifact"] = {"forged": True}
                    return httpx.Response(200, json=payload)
                return httpx.Response(reply.status_code,
                                      content=reply.content, headers=dict(reply.headers))
        return asyncio.run(forward())

    vault = DatasetVault()
    principal = Principal("buyer", "evaluation")
    required_calls = ("quote.render",) if expected_tool else ()
    vault.register(principal, Dataset(
        "buyer", "holdout-v1", "holdout",
        (Case("case-1", {"ok": True, "ref": "artifact://synthetic/output"},
              required_tool_calls=required_calls,
              input_ref="artifact://public-input"),)))
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / (eval_id + '.sqlite')}")
    metadata.create_all(engine)
    client = RuntimeEvidenceHTTPCollector(
        base_url="http://127.0.0.1:8010", service_token=token,
        transport=httpx.MockTransport(transport_handler))
    verifier = Ed25519EvidenceVerifier({
        "runtime-v1": RuntimeAuditPublicKey("buyer", private.public_key())})
    request = EvaluationRequest(
        "buyer", "artifact://agent-spec", spec.artifact_digest,
        "holdout-v1", "policy", eval_id+"-idem", eval_id)
    try:
        workflow = DurableEvaluationWorkflow(
            vault, client, SqlEvaluationJobStore(engine),
            verifier=verifier, clock=lambda: 100.0, worker_id="evaluator")
        assert workflow.submit(principal, request).status == "QUEUED"
        finished = workflow.process(principal, eval_id)
        events = SqlEvaluationJobStore(engine).pending_events(principal)
        assert requests and "/evaluation-evidence" in str(requests[0].url)
        assert "input_ref" not in str(requests[0].url)
        return finished, len(events)
    finally:
        client.close()
        engine.dispose()


def _run(audit, *, eval_id: str):
    return asyncio.run(audit.run_public_case(
        tenant_id="buyer", evaluation_run_id=eval_id, case_id="case-1",
        dataset_version_ref="holdout-v1",
        request="Produce one approved synthetic quotation draft"))


def test_real_runtime_quality_repair_with_sealed_holdout(tmp_path):
    # A polished assertion without actual tool output MUST fail.
    original, old_tools, old_private, old_audit = _agent(uses_tool=False)
    _run(old_audit, eval_id="baseline")
    first, first_events = _collect_and_evaluate(
        tmp_path, original, old_private, old_audit,
        eval_id="baseline", expected_tool=True)
    assert first.status == "FAILED"
    assert first.result is not None and not first.result.passed
    assert first_events == 1
    assert old_tools.called == []

    # Real GEPARD orchestration seam, with the explicitly mock optimization
    # backend; NEVER pass the sealed holdout into optimizer.
    optimizer = OptimizerAdapter()
    patch = optimizer.propose(OptimizationRequest(
        tenant_id="buyer", agent_spec_ref="artifact://original",
        baseline_spec_ref="artifact://original",
        existing_prompt=original.system_prompt,
        allowed_surfaces=("system_prompt",),
        tuning_dataset_refs=("tune-v1",), validation_dataset_refs=("validation-v1",),
    ))
    assert patch.status == "REQUIRES_INDEPENDENT_EVALUATION"
    assert optimizer.backend_name == "deterministic_mock_not_gepa"
    candidate_dict = original.model_dump(exclude={"artifact_digest"}, mode="json")
    candidate_dict["system_prompt"] = patch.replacement
    candidate_dict["agent_spec_version"] = original.agent_spec_version + "-candidate"
    candidate_spec = original.model_copy(update={
        "system_prompt": patch.replacement,
        "agent_spec_version": candidate_dict["agent_spec_version"],
        "artifact_digest": digest(candidate_dict),
    })
    assert candidate_spec.verify_digest()
    assert candidate_spec.artifact_digest != original.artifact_digest

    candidate, new_tools, new_private, new_audit = _agent(
        uses_tool=True, candidate_spec=candidate_spec)
    _run(new_audit, eval_id="candidate")
    passed, outbox_count = _collect_and_evaluate(
        tmp_path, candidate, new_private, new_audit,
        eval_id="candidate", expected_tool=True)
    assert passed.status == "PASSED"
    assert passed.result is not None
    assert passed.result.independent_acceptance
    assert passed.result.passed
    assert outbox_count == 1
    assert len(new_tools.called) == 1


def test_runtime_evidence_tampering_is_blocked_by_quality(tmp_path):
    spec, tools, private, audit = _agent(uses_tool=True)
    _run(audit, eval_id="tampered")
    blocked, count = _collect_and_evaluate(
        tmp_path, spec, private, audit, eval_id="tampered",
        expected_tool=True, corrupt=True)
    assert blocked.status == "BLOCKED"
    assert blocked.result is None
    assert len(tools.called) == 1
    assert count == 1
