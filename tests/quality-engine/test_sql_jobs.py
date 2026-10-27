import concurrent.futures
from dataclasses import replace

import pytest
from sqlalchemy import create_engine

from quality_engine.core import EvaluationRequest, EvaluationResult, Principal, InvalidEvidence, AccessDenied
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata


@pytest.fixture
def store(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    metadata.create_all(engine)
    return SqlEvaluationJobStore(engine)


def req(tenant="a"):
    return EvaluationRequest(tenant, "spec-ref", "digest-a", "ds-v1", "policy", "idem-1", "run-1")


def accepted():
    return EvaluationResult("run-1", "digest-a", "ds-v1", "PASSED", True, False,
                            1.0, 3, (), 0.12, 40, "test-digest", independent_acceptance=True, tenant_id="a")


def test_durable_submit_and_idempotency_and_tenant_guard(store):
    a = Principal("a", "evaluation")
    assert store.submit(a, req()).status == "QUEUED"
    assert store.submit(a, req()).run_id == "run-1"
    with pytest.raises(InvalidEvidence):
        store.submit(a, replace(req(), agent_spec_ref="bad"))
    with pytest.raises(InvalidEvidence):
        store.submit(a, replace(req(), idempotency_key="another"))
    with pytest.raises(AccessDenied):
        store.submit(Principal("b", "evaluation"), req())
    with pytest.raises(KeyError):
        store.get(Principal("b", "evaluation"), "run-1")


def test_claim_commit_and_outbox_atomically(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    claim = store.claim(a, run_id="run-1", worker_id="worker-A", now=100)
    assert claim.attempt == 1
    assert store.claim(a, run_id="run-1", worker_id="worker-B", now=101) is None
    job = store.complete(a, claim, now=102, status="PASSED", result=accepted())
    assert job.status == "PASSED" and job.result["independent_acceptance"]
    assert store.claim(a, run_id="run-1", worker_id="worker-A", now=102) is None
    events = store.pending_events(a)
    assert len(events) == 1
    assert events[0].payload["status"] == "PASSED"
    assert "gold" not in str(events[0].payload)
    assert store.mark_dispatched(a, events[0].event_id)
    assert not store.mark_dispatched(a, events[0].event_id)
    assert store.pending_events(a) == ()


def test_claim_fencing_after_crash_recovery(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    expired = store.claim(a, run_id="run-1", worker_id="worker-A", now=0, lease_seconds=5)
    recovered = store.claim(a, run_id="run-1", worker_id="worker-B", now=6, lease_seconds=5)
    assert recovered.attempt == 2
    with pytest.raises(InvalidEvidence, match="stale"):
        store.complete(a, expired, now=7, status="PASSED", result=accepted())
    assert store.pending_events(a) == ()
    store.complete(a, recovered, now=7, status="PASSED", result=accepted())
    assert len(store.pending_events(a)) == 1


def test_no_pass_without_real_passed_result(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    claim = store.claim(a, run_id="run-1", worker_id="w", now=0)
    with pytest.raises(InvalidEvidence):
        store.complete(a, claim, now=1, status="PASSED")
    with pytest.raises(InvalidEvidence):
        store.complete(a, claim, now=1, status="PASSED", result=replace(accepted(), hard_veto=True))
    assert store.pending_events(a) == ()


def test_multiple_threads_only_one_worker_claims(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'thread.db'}")
    metadata.create_all(engine)
    store = SqlEvaluationJobStore(engine)
    a = Principal("a", "evaluation")
    store.submit(a, req())
    def claim(index):
        return store.claim(a, run_id="run-1", worker_id=f"w{index}", now=0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        claims = list(pool.map(claim, range(5)))
    assert sum(c is not None for c in claims) == 1


def test_crash_does_not_mutate_released_task_without_claim(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    claim = store.claim(a, run_id="run-1", worker_id="w", now=0, lease_seconds=10, max_attempts=1)
    assert store.claim(a, run_id="run-1", worker_id="w2", now=100, max_attempts=1) is None
    with pytest.raises(InvalidEvidence):
        store.complete(a, claim, now=100, status="BLOCKED", error_code="LEASE_EXPIRED")



def test_only_independent_holdout_can_be_committed_as_passed(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    claim = store.claim(a, run_id="run-1", worker_id="w", now=1)
    with pytest.raises(InvalidEvidence, match="independent holdout"):
        store.complete(a, claim, now=2, status="PASSED",
                       result=replace(accepted(), independent_acceptance=False))
    with pytest.raises(InvalidEvidence):
        store.complete(a, claim, now=2, status="PASSED",
                       result=replace(accepted(), tenant_id="other"))
    assert store.pending_events(a) == ()


def test_exhausted_worker_lease_becomes_blocked_once(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    store.claim(a, run_id="run-1", worker_id="w", now=0, lease_seconds=10, max_attempts=1)
    assert store.block_exhausted(a, now=11, max_attempts=1) == 1
    assert store.get(a, "run-1").error_code == "MAX_ATTEMPTS_EXHAUSTED"
    assert store.block_exhausted(a, now=12, max_attempts=1) == 0
    assert len(store.pending_events(a)) == 1


def test_invalid_nonfinite_worker_clock_is_rejected(store):
    a = Principal("a", "evaluation")
    store.submit(a, req())
    with pytest.raises(ValueError):
        store.claim(a, run_id="run-1", worker_id="w", now=float("nan"))
