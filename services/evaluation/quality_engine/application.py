"""Contract-first evaluation workflow; external evidence comes only from a trusted port.

This is an in-memory prototype, not durable production scheduling. The work
queue and trusted evidence collector must be replaced by real authenticated
runtime audit records before release.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from threading import RLock

from .execution_evidence import (
    PublicRunCase, EvidenceEnvelope, EvidenceCollector, EvidenceVerifier, collect_observations,
)
from .core import (
    AccessDenied, Case, DatasetVault, EvaluationEngine, EvaluationPolicy,
    EvaluationRequest, EvaluationResult, InvalidEvidence, ObservedRun, Principal,
)


@dataclass(frozen=True)
class EvaluationJob:
    tenant_id: str
    evaluation_run_id: str
    idempotency_key: str
    status: str
    result: EvaluationResult | None = None
    error_code: str | None = None


class EvaluationWorkflow:
    """Single-process reference; caller identity validated before reading state."""

    def __init__(self, vault: DatasetVault, collector: EvidenceCollector,
                 policy: EvaluationPolicy | None = None,
                 verifier: EvidenceVerifier | None = None,
                 require_attestation: bool = False):
        self._vault = vault
        self._engine = EvaluationEngine(vault)
        self._collector = collector
        self._policy = policy or EvaluationPolicy()
        self._verifier = verifier
        self._require_attestation = require_attestation
        if require_attestation and verifier is None:
            raise ValueError("a verifier is mandatory when attestation is required")
        self._requests: dict[tuple[str, str], EvaluationRequest] = {}
        self._jobs: dict[tuple[str, str], EvaluationJob] = {}
        self._idem: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    @staticmethod
    def _check(principal: Principal, tenant_id: str) -> None:
        if principal.role != "evaluation" or principal.tenant_id != tenant_id:
            raise AccessDenied("trusted evaluator identity required for tenant")

    def submit(self, principal: Principal, request: EvaluationRequest) -> EvaluationJob:
        self._check(principal, request.tenant_id)
        if not all((request.evaluation_run_id, request.idempotency_key,
                    request.agent_spec_ref, request.agent_spec_digest,
                    request.policy_ref, request.dataset_version_ref)):
            raise InvalidEvidence("evaluation request needs pinned identities")
        self._vault.read(principal, request.dataset_version_ref)
        job_key = (request.tenant_id, request.evaluation_run_id)
        idem_key = (request.tenant_id, request.idempotency_key)
        with self._lock:
            previous = self._idem.get(idem_key)
            if previous is not None:
                prior = self._requests[(request.tenant_id, previous)]
                if prior != request:
                    raise InvalidEvidence("idempotency conflict")
                return self._jobs[(request.tenant_id, previous)]
            if job_key in self._jobs:
                raise InvalidEvidence("evaluation_run_id already assigned")
            job = EvaluationJob(request.tenant_id, request.evaluation_run_id,
                                request.idempotency_key, "QUEUED")
            self._idem[idem_key] = request.evaluation_run_id
            self._jobs[job_key] = job
            self._requests[job_key] = request
            return job

    def get(self, principal: Principal, evaluation_run_id: str) -> EvaluationJob:
        self._check(principal, principal.tenant_id)
        key = (principal.tenant_id, evaluation_run_id)
        with self._lock:
            if key not in self._jobs:
                raise KeyError("unknown evaluation run")
            return self._jobs[key]

    def process(self, principal: Principal, evaluation_run_id: str) -> EvaluationJob:
        """Worker hook; deliberately NOT triggered by untrusted HTTP request."""
        job = self.get(principal, evaluation_run_id)
        key = (principal.tenant_id, evaluation_run_id)
        with self._lock:
            # Re-read under lock: another worker may have claimed the job.
            job = self._jobs[key]
            if job.status in ("PASSED", "FAILED", "BLOCKED"):
                return job
            if job.status != "QUEUED":
                raise InvalidEvidence("run already executing")
            self._jobs[key] = replace(job, status="RUNNING")
        request = self._requests[key]
        try:
            dataset = self._vault.read(principal, request.dataset_version_ref)
            observations = collect_observations(
                self._collector, request, dataset.cases, self._verifier, self._require_attestation
            )
            result = self._engine.evaluate(principal, request, observations, self._policy)
            completed = replace(job, status=result.status, result=result)
        except (InvalidEvidence, AccessDenied):
            completed = replace(job, status="BLOCKED", error_code="INVALID_EXECUTION_EVIDENCE")
        except Exception:
            # Never return raw exception text: runtime exceptions may contain credentials.
            completed = replace(job, status="BLOCKED", error_code="EVIDENCE_COLLECTOR_UNAVAILABLE")
        with self._lock:
            self._jobs[key] = completed
        return completed
