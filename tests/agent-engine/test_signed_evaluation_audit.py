"""Genuine Agent04 Runtime -> verified ToolGateway -> Ed25519 audit -> HTTP tests.

Only synthetic business tools are used; this is not proof of deployed
Agent05 Evaluation, key management, or production service IAM.
"""
from __future__ import annotations

import json

import httpx
import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent_runtime import Decision, EffectLedger, Runtime, RuntimeDenied, ToolPolicy
from agent_runtime.evaluation_audit import (
    EvidenceRecordingGateway,
    RuntimeAuditReadAPI,
    SignedRuntimeAudit,
)
from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task


def fixture(*, blocked: bool = False):
    spec = build(
        task("audit-draft", ["draft"], ["draft_file"], ["draft:write"]),
        Registry([manifest("document.render", ["draft"], ["draft_file"], ["draft:write"])]),
    )
    binding = spec.selected_tools[0]
    policy = ToolPolicy(
        tenant_id=spec.tenant_id,
        tool_id=binding.tool_id,
        version=binding.version,
        manifest_digest=binding.digest,
        scopes=frozenset(binding.granted_scopes),
        effect_mode="draft_file",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    tools = FakeTools()
    decisions = ([Decision(kind="tool", tool_id="unauthorized.pay")]
                 if blocked else [
                     Decision(kind="tool", tool_id=binding.tool_id, args={}),
                     Decision(kind="final", text="I successfully completed the task"),
                 ])
    gateway = EvidenceRecordingGateway(
        tools, EffectLedger(), policies={binding.tool_id: policy})
    runtime = Runtime(
        ScriptedModel(decisions), gateway,
        approved_spec_digests=frozenset({spec.artifact_digest}))
    private = Ed25519PrivateKey.generate()
    producer = SignedRuntimeAudit(
        runtime, spec, private_key=private, key_id="runtime-tenant-buyer-v1")
    return spec, tools, producer, private


def verify_signature(payload: dict, key: Ed25519PrivateKey) -> None:
    canonical = json.dumps(payload["envelope"], sort_keys=True, separators=(",", ":"),
                           allow_nan=False).encode("utf-8")
    key.public_key().verify(bytes.fromhex(payload["signature_hex"]), canonical)


async def run(producer, *, dataset: str = "holdout-v1"):
    return await producer.run_public_case(
        tenant_id="buyer", evaluation_run_id="eval-1", case_id="case-1",
        dataset_version_ref=dataset, request="Render an authorized draft document")


@pytest.mark.asyncio
async def test_real_verified_runtime_result_signed_with_quality_exact_schema():
    spec, tools, producer, private = fixture()
    signed = await run(producer)
    verify_signature(signed, private)
    envelope = signed["envelope"]
    assert set(envelope) == {
        "tenant_id", "agent_spec_digest", "dataset_version_ref", "case_id",
        "trace_ref", "observation", "evaluation_run_id"}
    assert envelope["agent_spec_digest"] == spec.artifact_digest
    assert envelope["evaluation_run_id"] == "eval-1"
    assert envelope["case_id"] == "case-1"
    observation = envelope["observation"]
    assert set(observation) == {
        "case_id", "artifact", "tool_calls", "steps", "latency_ms",
        "token_count", "cost_usd", "safety_violations",
        "memory_violations", "graph_events", "memory_reads"}
    # The business artifact is the gateway-validated tool response,
    # not the final assistant text.
    assert observation["artifact"] == {"ok": True, "ref": "artifact://synthetic/output"}
    assert observation["artifact"] != "I successfully completed the task"
    assert observation["tool_calls"] == [{
        "tool_id": "document.render", "arguments_valid": True,
        "approved": True, "effect_proof": signed["envelope"]["observation"]["tool_calls"][0]["effect_proof"]}]
    assert observation["tool_calls"][0]["effect_proof"].startswith("sha256:")
    assert observation["steps"] == 2
    assert observation["graph_events"] == ["final"]
    assert len(tools.called) == 1
    # Re-reading or retrying the same immutable job cannot repeat a draft write.
    assert await run(producer) == signed
    assert len(tools.called) == 1
    with pytest.raises(RuntimeDenied, match="AUDIT_IDEMPOTENCY_CONFLICT"):
        await run(producer, dataset="different-dataset")


@pytest.mark.asyncio
async def test_signed_evidence_http_contract_and_tenant_acl():
    spec, tools, producer, private = fixture()
    await run(producer)
    token_to_tenant = {"correct": "buyer", "other": "supplier"}
    api = RuntimeAuditReadAPI(producer, authenticate=token_to_tenant.get)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api), base_url="http://internal"
    ) as client:
        path = "/internal/agent-runs/eval-1%3Acase-1/evaluation-evidence"
        params = {
            "case_id": "case-1", "tenant_id": "buyer",
            "agent_spec_digest": spec.artifact_digest,
            "dataset_version_ref": "holdout-v1",
        }
        good = await client.get(path, params=params, headers={"Authorization": "Bearer correct"})
        assert good.status_code == 200
        assert good.headers["cache-control"] == "no-store"
        verify_signature(good.json(), private)
        assert len(tools.called) == 1

        no_auth = await client.get(path, params=params)
        assert no_auth.status_code == 401
        foreign = await client.get(path, params=params,
                                   headers={"Authorization": "Bearer other"})
        assert foreign.status_code == 404
        tampered = await client.get(
            path, params={**params, "agent_spec_digest": "not-approved"},
            headers={"Authorization": "Bearer correct"})
        assert tampered.status_code == 404
        wrong_case = await client.get(
            path, params={**params, "case_id": "case-2"},
            headers={"Authorization": "Bearer correct"})
        assert wrong_case.status_code == 404
        replay_attempt = await client.post(
            path, json={"execution": "run-again"},
            headers={"Authorization": "Bearer correct"})
        assert replay_attempt.status_code == 405
    assert len(tools.called) == 1


@pytest.mark.asyncio
async def test_blocked_runtime_does_not_sign_a_fabricated_success():
    _spec, tools, producer, private = fixture(blocked=True)
    result = await run(producer)
    verify_signature(result, private)
    observation = result["envelope"]["observation"]
    assert observation["artifact"] is None
    assert observation["tool_calls"] == []
    assert observation["safety_violations"] == ["TOOL_DENIED"]
    assert observation["graph_events"] == ["blocked"]
    assert not tools.called


@pytest.mark.asyncio
async def test_audit_rejects_cross_tenant_and_malformed_job_ids():
    _spec, tools, producer, _private = fixture()
    with pytest.raises(RuntimeDenied, match="AUDIT_TENANT_DENIED"):
        await producer.run_public_case(
            tenant_id="supplier", evaluation_run_id="eval-1", case_id="case-1",
            dataset_version_ref="holdout-v1", request="Do business task")
    with pytest.raises(RuntimeDenied, match="INVALID_AUDIT_IDENTITY"):
        await producer.run_public_case(
            tenant_id="buyer", evaluation_run_id="../escape", case_id="case-1",
            dataset_version_ref="holdout-v1", request="Do business task")
    assert not tools.called


@pytest.mark.asyncio
async def test_tampered_payload_cannot_verify_under_runtime_public_key():
    _spec, _tools, producer, private = fixture()
    signed = await run(producer)
    signed_copy = json.loads(json.dumps(signed))
    signed_copy["envelope"]["observation"]["artifact"]["ok"] = False
    with pytest.raises(InvalidSignature):
        verify_signature(signed_copy, private)
