from dataclasses import replace

from sqlalchemy import create_engine

from quality_engine.application import EvidenceEnvelope
from quality_engine.attestation import HmacEvidenceVerifier
from quality_engine.core import Case, Dataset, EvaluationRequest, ObservedRun, Principal, ToolCall
from quality_engine.durable_workflow import DurableEvaluationWorkflow
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata as job_metadata
from quality_engine.sql_vault import SqlDatasetVault, metadata as gold_metadata
from quality_engine.gold_crypto import AesGcmGoldCipher


class SignedCollector:
    def __init__(self, signer, *, bad=False):
        self.signer = signer
        self.bad = bad
        self.calls = 0

    def collect(self, req, case):
        self.calls += 1
        assert not hasattr(case, "expected_artifact")
        value = EvidenceEnvelope(req.tenant_id, req.agent_spec_digest,
                                 req.dataset_version_ref, case.case_id, "trace://audit",
                                 ObservedRun(case.case_id, {"verified": True},
                                             (ToolCall("catalog.lookup", effect_proof="effect:1"),),
                                             graph_events=("tool.call", "final")))
        signed = self.signer.sign(value, key_id="runtime")
        return replace(signed, signature_hex="00"*32) if self.bad else signed


def create(tmp_path, bad=False):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'eval.db'}")
    job_metadata.create_all(engine)
    gold_metadata.create_all(engine)
    vault = SqlDatasetVault(engine, cipher=AesGcmGoldCipher(lambda t: b"c"*32))
    owner = Principal("a", "evaluation")
    vault.register(owner, Dataset("a", "holdout-v1", "holdout", (
        Case("r1", {"verified": True}, ("catalog.lookup",), ("effect:1",),
             input_ref="artifact://input"),)))
    signer = HmacEvidenceVerifier({"runtime": b"a"*32})
    collector = SignedCollector(signer, bad=bad)
    store = SqlEvaluationJobStore(engine)
    req = EvaluationRequest("a", "agent-a", "sha256:a", "holdout-v1", "policy", "idemp", "run-1")
    workflow = DurableEvaluationWorkflow(vault, collector, store, verifier=signer, clock=lambda: 100)
    return engine, vault, owner, signer, collector, store, req, workflow

 
import pytest

@pytest.fixture
def scenario(tmp_path):
    values = create(tmp_path)
    yield values
    values[0].dispose()

@pytest.fixture
def forged_scenario(tmp_path):
    values = create(tmp_path, bad=True)
    yield values
    values[0].dispose()


def test_persisted_end_to_end_evaluation_and_outbox(scenario):
    engine, vault, owner, signer, collector, store, req, wf = scenario
    assert wf.submit(owner, req).status == "QUEUED"
    result = wf.process(owner, req.evaluation_run_id)
    assert result.status == "PASSED"
    assert result.result.independent_acceptance
    assert collector.calls == 1
    assert wf.process(owner, req.evaluation_run_id).status == "PASSED"
    assert collector.calls == 1
    events = store.pending_events(owner)
    assert len(events) == 1 and events[0].payload["passed"]
    new = DurableEvaluationWorkflow(SqlDatasetVault(engine, cipher=AesGcmGoldCipher(lambda t: b"c"*32)), SignedCollector(signer),
                                    SqlEvaluationJobStore(engine), verifier=signer, clock=lambda: 100)
    assert new.get(owner, "run-1").result.independent_acceptance
    assert new.submit(owner, req).status == "PASSED"


def test_forged_trace_blocks_without_leaking_gold(forged_scenario):
    _, _, owner, _, _, store, req, wf = forged_scenario
    wf.submit(owner, req)
    result = wf.process(owner, "run-1")
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EXECUTION_EVIDENCE"
    events = store.pending_events(owner)
    assert events[0].payload["passed"] is False
    assert "verified" not in str(events[0].payload)


def test_cross_tenant_durable_eval_is_invisible(scenario):
    _, _, owner, _, _, _, req, wf = scenario
    wf.submit(owner, req)
    from quality_engine import AccessDenied
    import pytest
    with pytest.raises((KeyError, AccessDenied)):
        wf.get(Principal("b", "evaluation"), "run-1")
    with pytest.raises(AccessDenied):
        wf.submit(Principal("b", "evaluation"), req)


def test_tuning_dataset_never_sticks_as_running_or_publishes_pass(scenario):
    _, vault, owner, _, _, store, req, wf = scenario
    vault.register(owner, Dataset("a", "tune-v1", "tune", (
        Case("r1", {"verified": True}, ("catalog.lookup",), ("effect:1",),
             input_ref="artifact://train-only"),)))
    training = replace(req, dataset_version_ref="tune-v1",
                       idempotency_key="train", evaluation_run_id="train-run")
    assert wf.submit(owner, training).status == "QUEUED"
    result = wf.process(owner, "train-run")
    assert result.status == "BLOCKED"
    assert result.error_code == "INDEPENDENT_HOLDOUT_REQUIRED"
    assert store.get(owner, "train-run").status == "BLOCKED"
    assert [e.payload["passed"] for e in store.pending_events(owner)] == [False]


def test_durable_fastapi_accept_poll_and_restart(scenario):
    from fastapi.testclient import TestClient
    from quality_engine.api import create_app
    from dataclasses import asdict
    engine, _, owner, signer, _, _, req, workflow = scenario
    client = TestClient(create_app(workflow, lambda: owner))
    payload = asdict(req)
    response = client.post("/internal/evaluations", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert client.get("/internal/evaluations/run-1").json()["status"] == "QUEUED"
    assert workflow.process(owner, "run-1").status == "PASSED"
    fresh = DurableEvaluationWorkflow(
        SqlDatasetVault(engine, cipher=AesGcmGoldCipher(lambda t: b"c" * 32)),
        SignedCollector(signer), SqlEvaluationJobStore(engine),
        verifier=signer, clock=lambda: 100)
    restart_client = TestClient(create_app(fresh, lambda: owner))
    assert restart_client.get("/internal/evaluations/run-1").json()["result"]["independent_acceptance"] is True
    assert restart_client.post("/internal/evaluations", json=payload).status_code == 202


def test_durable_fastapi_rejects_cross_tenant_http(scenario):
    from fastapi.testclient import TestClient
    from quality_engine.api import create_app
    from dataclasses import asdict
    _, _, owner, _, _, _, req, workflow = scenario
    client = TestClient(create_app(workflow, lambda: Principal("other", "evaluation")))
    assert client.post("/internal/evaluations", json=asdict(req)).status_code == 403
    assert client.get("/internal/evaluations/run-1").status_code == 404


def test_durable_workflow_with_runtime_ed25519_verify_only_key(scenario):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from quality_engine.ed25519_audit import Ed25519EvidenceVerifier, RuntimeAuditPublicKey
    from quality_engine.attestation import AttestedEvidence, canonical_evidence
    engine, vault, owner, _, _, store, request, _ = scenario
    private = Ed25519PrivateKey.generate()  # synthetic Runtime-only signer
    verifier = Ed25519EvidenceVerifier({
        "runtime-v1": RuntimeAuditPublicKey("a", private.public_key())})

    class RuntimeSignedCollector:
        def collect(self, req, case):
            assert not hasattr(case, "expected_artifact")
            envelope = EvidenceEnvelope(
                req.tenant_id, req.agent_spec_digest, req.dataset_version_ref,
                case.case_id, "trace://audit",
                ObservedRun(case.case_id, {"verified": True},
                            (ToolCall("catalog.lookup", effect_proof="effect:1"),),
                            graph_events=("tool.call", "final")))
            return AttestedEvidence(envelope, "runtime-v1",
                                    private.sign(canonical_evidence(envelope)).hex())

    workflow = DurableEvaluationWorkflow(vault, RuntimeSignedCollector(), store,
                                         verifier=verifier, clock=lambda: 100)
    assert workflow.submit(owner, request).status == "QUEUED"
    assert workflow.process(owner, request.evaluation_run_id).status == "PASSED"
    assert not hasattr(verifier, "sign")


def test_slow_signed_evaluation_renews_lease_and_commits(scenario):
    """A slow model-backed evaluation must not lose its worker lease."""
    import time
    engine, vault, owner, signer, _, store, request, _ = scenario

    class SlowCollector(SignedCollector):
        def collect(self, req, case):
            time.sleep(0.38)
            return super().collect(req, case)

    runner = DurableEvaluationWorkflow(
        vault, SlowCollector(signer), store,
        verifier=signer, clock=time.time,
        worker_id="slow-real-clock", lease_seconds=0.24,
    )
    assert runner.submit(owner, request).status == "QUEUED"
    result = runner.process(owner, request.evaluation_run_id)
    assert result.status == "PASSED"
    assert len(store.pending_events(owner)) == 1
