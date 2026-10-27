"""Durable evaluation service on SQL job leases and signed evidence.

A private worker identity performs processing. HTTP clients only submit jobs.
Fenced updates prevent obsolete workers from committing; outbox persists
completion events in the same SQL transaction as the result.
"""
from __future__ import annotations

from time import time
from typing import Callable

from .application import EvaluationJob
from .datasets import DatasetVault
from .evaluation import EvaluationEngine, EvaluationPolicy, EvaluationRequest, EvaluationResult, Finding
from .execution_evidence import EvidenceCollector, EvidenceVerifier, collect_observations
from .primitives import AccessDenied, InvalidEvidence, Principal
from .sql_jobs import SqlEvaluationJobStore, JobRecord


def as_job(record: JobRecord) -> EvaluationJob:
    result = None
    if record.result is not None:
        body = dict(record.result)
        body["findings"] = tuple(Finding(**f) for f in body["findings"])
        result = EvaluationResult(**body)
    return EvaluationJob(record.tenant_id, record.run_id, "", record.status,
                         result=result, error_code=record.error_code)


class DurableEvaluationWorkflow:
    def __init__(self, vault: DatasetVault, collector: EvidenceCollector,
                 store: SqlEvaluationJobStore, *,
                 verifier: EvidenceVerifier, policy: EvaluationPolicy | None = None,
                 clock: Callable[[], float] = time,
                 worker_id: str = "evaluator-01", lease_seconds: float = 60.0):
        if verifier is None:
            raise ValueError("durable workflow requires signed runtime evidence")
        if not worker_id or lease_seconds <= 0:
            raise ValueError("worker identity and lease required")
        self._vault, self._collector, self._store = vault, collector, store
        self._verifier = verifier
        self._engine = EvaluationEngine(vault)
        self._policy = policy or EvaluationPolicy()
        self._clock, self._worker_id, self._lease_seconds = clock, worker_id, lease_seconds

    def submit(self, principal: Principal, request: EvaluationRequest) -> EvaluationJob:
        if principal.role != "evaluation" or principal.tenant_id != request.tenant_id:
            raise AccessDenied("tenant principal required")
        self._vault.read(principal, request.dataset_version_ref)
        return as_job(self._store.submit(principal, request))

    def get(self, principal: Principal, evaluation_run_id: str) -> EvaluationJob:
        return as_job(self._store.get(principal, evaluation_run_id))

    def process(self, principal: Principal, evaluation_run_id: str) -> EvaluationJob:
        claim = self._store.claim(principal, run_id=evaluation_run_id,
                                  worker_id=self._worker_id, now=self._clock(),
                                  lease_seconds=self._lease_seconds)
        if claim is None:
            return self.get(principal, evaluation_run_id)
        try:
            ds = self._vault.read(principal, claim.request.dataset_version_ref)
            observations = collect_observations(self._collector, claim.request, ds.cases,
                                                self._verifier, True)
            result = self._engine.evaluate(principal, claim.request, observations, self._policy)
            status, code = result.status, None
        except (InvalidEvidence, AccessDenied):
            status, code, result = "BLOCKED", "INVALID_EXECUTION_EVIDENCE", None
        except Exception:
            status, code, result = "BLOCKED", "EVIDENCE_COLLECTOR_UNAVAILABLE", None
        return as_job(self._store.complete(principal, claim, now=self._clock(),
                                           status=status, result=result, error_code=code))
