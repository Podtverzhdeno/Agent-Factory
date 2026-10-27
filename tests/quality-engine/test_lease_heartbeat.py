import time

import pytest
from sqlalchemy import create_engine

from quality_engine.core import EvaluationRequest, Principal, InvalidEvidence
from quality_engine.lease_heartbeat import LeaseKeeper
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata


@pytest.fixture
def state(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'lease.sqlite'}")
    metadata.create_all(engine)
    store = SqlEvaluationJobStore(engine)
    principal = Principal("a", "evaluation")
    request = EvaluationRequest("a", "spec", "digest", "dataset", "policy", "key", "run")
    store.submit(principal, request)
    yield store, principal
    engine.dispose()


def test_renewal_blocks_competing_worker_and_old_claim_after_takeover(state):
    store, owner = state
    old = store.claim(owner, run_id="run", worker_id="first", now=0, lease_seconds=10)
    assert store.renew_lease(owner, old, now=6, lease_seconds=10) == 16
    assert store.claim(owner, run_id="run", worker_id="second", now=12) is None
    with pytest.raises(InvalidEvidence):
        store.renew_lease(owner, old, now=17)
    fresh = store.claim(owner, run_id="run", worker_id="second", now=17)
    assert fresh and fresh.attempt == 2
    with pytest.raises(InvalidEvidence):
        store.renew_lease(owner, old, now=18)


def test_renewal_rejects_foreign_tenant_and_invalid_clocks(state):
    store, owner = state
    claim = store.claim(owner, run_id="run", worker_id="first", now=0)
    with pytest.raises(PermissionError):
        store.renew_lease(Principal("other", "evaluation"), claim, now=1)
    with pytest.raises(ValueError):
        store.renew_lease(owner, claim, now=float("nan"))
    with pytest.raises(ValueError):
        store.renew_lease(owner, claim, now=1, lease_seconds=float("inf"))
    with pytest.raises(InvalidEvidence):
        store.renew_lease(owner, claim, now=1, lease_seconds=1)


def test_leasekeeper_heartbeats_while_slow_evaluation_runs(state):
    store, owner = state
    now = time.time()
    claim = store.claim(owner, run_id="run", worker_id="slow-worker", now=now, lease_seconds=0.24)
    with LeaseKeeper(store, owner, claim, lease_seconds=0.24):
        time.sleep(0.40)
        assert store.claim(owner, run_id="run", worker_id="competitor", now=time.time()) is None
    time.sleep(0.27)
    new = store.claim(owner, run_id="run", worker_id="competitor", now=time.time())
    assert new and new.attempt == 2
