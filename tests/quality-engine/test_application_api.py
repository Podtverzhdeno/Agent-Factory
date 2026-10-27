"""Contract-first workflow and HTTP adapter tests, no production transport."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from quality_engine.application import EvaluationWorkflow
from quality_engine.api import create_app
from quality_engine.core import (
    AccessDenied, Case, Dataset, DatasetVault, EvaluationRequest,
    InvalidEvidence, ObservedRun, Principal, ToolCall,
)


class FakeEvidenceCollector:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    def collect(self, request, case):
        if self.fail:
            raise RuntimeError("sensitive-credential-from-upstream")
        self.calls.append((request.agent_spec_ref, case.case_id))
        return ObservedRun(case.case_id, case.expected_artifact,
                           (ToolCall("lookup", effect_proof="proof:read"),),
                           graph_events=("tool.call", "tool.result"))


@pytest.fixture
def workflow():
    vault = DatasetVault()
    owner = Principal("tenant-a", "evaluation")
    vault.register(owner, Dataset("tenant-a", "holdout-v1", "holdout",
                                 (Case("c", {"ok": 1}, ("lookup",), ("proof:read",)),)))
    collector = FakeEvidenceCollector()
    return EvaluationWorkflow(vault, collector), owner, collector


def req():
    return EvaluationRequest("tenant-a", "spec:a", "sha256:ab", "holdout-v1",
                             "policy:p1", "idem:1", "run:1")


def test_async_submit_does_not_falsely_claim_run_complete(workflow):
    wf, owner, collector = workflow
    job = wf.submit(owner, req())
    assert job.status == "QUEUED" and collector.calls == []
    assert wf.get(owner, req().evaluation_run_id).status == "QUEUED"


def test_worker_produces_independent_result(workflow):
    wf, owner, collector = workflow
    wf.submit(owner, req())
    job = wf.process(owner, "run:1")
    assert job.status == "PASSED"
    assert job.result is not None and job.result.independent_acceptance
    assert collector.calls == [("spec:a", "c")]
    assert wf.process(owner, "run:1") == job


def test_submit_idempotency_and_conflict(workflow):
    wf, owner, collector = workflow
    first = wf.submit(owner, req())
    assert wf.submit(owner, req()) == first
    with pytest.raises(InvalidEvidence):
        wf.submit(owner, replace(req(), agent_spec_ref="spec:b"))
    with pytest.raises(InvalidEvidence):
        wf.submit(owner, replace(req(), idempotency_key="idem:other"))


def test_cross_tenant_submit_and_read_denied(workflow):
    wf, owner, _ = workflow
    wf.submit(owner, req())
    with pytest.raises(AccessDenied):
        wf.submit(Principal("tenant-b", "evaluation"), req())
    with pytest.raises(KeyError):
        wf.get(Principal("tenant-b", "evaluation"), "run:1")
    with pytest.raises(AccessDenied):
        wf.get(Principal("tenant-a", "builder"), "run:1")


def test_worker_failure_blocks_without_leaking_exception(workflow):
    wf, owner, _ = workflow
    wf._collector = FakeEvidenceCollector(fail=True)
    wf.submit(owner, req())
    job = wf.process(owner, "run:1")
    assert job.status == "BLOCKED"
    assert job.error_code == "EVIDENCE_COLLECTOR_UNAVAILABLE"
    assert "sensitive-credential" not in str(job)


def test_http_queued_then_processed_and_schema_guard(workflow):
    wf, owner, _ = workflow
    client = TestClient(create_app(wf, lambda: owner))
    payload = vars(req())
    response = client.post("/internal/evaluations", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert client.get("/internal/evaluations/run:1").json()["status"] == "QUEUED"
    wf.process(owner, "run:1")
    response = client.get("/internal/evaluations/run:1")
    assert response.status_code == 200
    assert response.json()["status"] == "PASSED"
    assert response.json()["result"]["independent_acceptance"] is True
    assert client.post("/internal/evaluations", json={**payload, "raw_gold": {"answer":"secret"}}).status_code == 422


def test_http_forbidden_principal_and_safe_notfound(workflow):
    wf, owner, _ = workflow
    client = TestClient(create_app(wf, lambda: Principal("tenant-b", "evaluation")))
    assert client.post("/internal/evaluations", json=vars(req())).status_code == 403
    assert client.get("/internal/evaluations/run:1").status_code == 404
    assert TestClient(create_app(wf, lambda: owner)).get("/internal/evaluations/nope").status_code == 404
