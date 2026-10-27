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
