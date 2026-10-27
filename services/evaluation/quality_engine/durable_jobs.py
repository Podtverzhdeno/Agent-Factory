"""Durable Evaluation workflow and atomic job claims using service-owned SQL tables.

Works with PostgreSQL via SQLAlchemy+psycopg; SQLite is for component tests.
No claim of operational deployment, scheduler, outbox or exactly-once side effects.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Callable

from sqlalchemy import (Column, Float, Integer, MetaData, String, Table,
                        UniqueConstraint, insert, select, update)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .application import EvidenceCollector, EvaluationJob, EvidenceEnvelope, PublicRunCase
from .core import (
    AccessDenied, DatasetVault, EvaluationEngine, EvaluationPolicy,
    EvaluationRequest, EvaluationResult, Finding, InvalidEvidence, Principal,
)


_METADATA = MetaData()
_JOBS = Table(
    "evaluation_jobs", _METADATA,
    Column("tenant_id", String(160), primary_key=True),
    Column("run_id", String(160), primary_key=True),
    Column("idempotency_key", String(240), nullable=False),
    Column("request_json", String, nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("lease_until", Float, nullable=False),
    Column("result_json", String),
    Column("error_code", String(96)),
    UniqueConstraint("tenant_id", "idempotency_key", name="uq_eval_tenant_idempotency"),
)


class SqlJobRepository:
    def __init__(self, engine: Engine, *, clock: Callable[[], float] = time.time):
        if engine.url.get_backend_name() not in ("postgresql", "sqlite"):
            raise ValueError("PostgreSQL production or SQLite test backend required")
        self.engine = engine
        self.clock = clock

    def bootstrap_schema(self) -> None:
        """Development/test only; production migration tooling runs outside this service."""
        _METADATA.create_all(self.engine)

    @staticmethod
    def _check(principal: Principal, tenant_id: str) -> None:
        if principal.role != "evaluation" or principal.tenant_id != tenant_id:
            raise AccessDenied("evaluation worker identity required")

    @staticmethod
    def _decode(row) -> EvaluationJob:
        result = None
        if row["result_json"]:
            data = json.loads(row["result_json"])
            data["findings"] = tuple(Finding(**f) for f in data["findings"])
            result = EvaluationResult(**data)
        return EvaluationJob(row["tenant_id"], row["run_id"], row["idempotency_key"],
                             row["status"], result, row["error_code"])

    def submit(self, principal: Principal, request: EvaluationRequest) -> EvaluationJob:
        self._check(principal, request.tenant_id)
        if not all((request.evaluation_run_id, request.idempotency_key, request.agent_spec_ref,
                    request.agent_spec_digest, request.dataset_version_ref, request.policy_ref)):
            raise InvalidEvidence("missing pinned evaluation command")
        canonical = json.dumps(asdict(request), sort_keys=True, separators=(",", ":"))
        values = dict(tenant_id=request.tenant_id, run_id=request.evaluation_run_id,
                      idempotency_key=request.idempotency_key, request_json=canonical,
                      status="QUEUED", attempts=0, lease_until=0)
        try:
            with self.engine.begin() as conn:
                conn.execute(insert(_JOBS).values(**values))
        except IntegrityError as exc:
            with self.engine.connect() as conn:
                old = conn.execute(select(_JOBS).where(
                    _JOBS.c.tenant_id == request.tenant_id,
                    _JOBS.c.idempotency_key == request.idempotency_key)).mappings().first()
            if old and old["request_json"] == canonical:
                return self._decode(old)
            raise InvalidEvidence("conflicting evaluation ID or idempotency key") from exc
        return EvaluationJob(request.tenant_id, request.evaluation_run_id,
                             request.idempotency_key, "QUEUED")

    def get(self, principal: Principal, run_id: str) -> EvaluationJob:
        self._check(principal, principal.tenant_id)
        with self.engine.connect() as conn:
            row = conn.execute(select(_JOBS).where(
                _JOBS.c.tenant_id == principal.tenant_id,
                _JOBS.c.run_id == run_id)).mappings().first()
        if row is None:
            raise KeyError("evaluation run not found")
        return self._decode(row)

    def claim(self, principal: Principal, run_id: str, *, lease_seconds: float = 120.0,
              max_attempts: int = 3) -> EvaluationRequest | None:
        self._check(principal, principal.tenant_id)
        if lease_seconds <= 0 or max_attempts < 1:
            raise ValueError("lease and retries must be bounded")
        now = self.clock()
        with self.engine.begin() as conn:
            # Atomic CAS across processes using UPDATE rowcount (not in-memory lock).
            row = conn.execute(select(_JOBS).where(
                _JOBS.c.tenant_id == principal.tenant_id,
                _JOBS.c.run_id == run_id)).mappings().first()
            if not row:
                raise KeyError("evaluation run not found")
            if row["status"] in ("PASSED", "FAILED", "BLOCKED"):
                return None
            if row["status"] == "RUNNING" and row["lease_until"] > now:
                return None
            if row["attempts"] >= max_attempts:
                conn.execute(update(_JOBS).where(
                    _JOBS.c.tenant_id == principal.tenant_id, _JOBS.c.run_id == run_id,
                    _JOBS.c.attempts == row["attempts"], _JOBS.c.status == row["status"])
                    .values(status="BLOCKED", error_code="ATTEMPTS_EXHAUSTED"))
                return None
            result = conn.execute(update(_JOBS).where(
                _JOBS.c.tenant_id == principal.tenant_id,
                _JOBS.c.run_id == run_id,
                _JOBS.c.status == row["status"],
                _JOBS.c.attempts == row["attempts"],
                _JOBS.c.lease_until == row["lease_until"])
                .values(status="RUNNING", attempts=row["attempts"] + 1,
                        lease_until=now + lease_seconds, error_code=None))
            if result.rowcount != 1:
                return None
            return EvaluationRequest(**json.loads(row["request_json"]))

    def complete(self, principal: Principal, run_id: str, result: EvaluationResult) -> None:
        self._check(principal, result.tenant_id)
        if result.evaluation_run_id != run_id or result.status not in ("PASSED", "FAILED"):
            raise InvalidEvidence("result does not match claimed run")
        with self.engine.begin() as conn:
            updated = conn.execute(update(_JOBS).where(
                _JOBS.c.tenant_id == principal.tenant_id, _JOBS.c.run_id == run_id,
                _JOBS.c.status == "RUNNING").values(
                    status=result.status,
                    result_json=json.dumps(asdict(result), sort_keys=True),
                    lease_until=0, error_code=None))
            if updated.rowcount != 1:
                raise InvalidEvidence("worker lost the job lease")

    def abort(self, principal: Principal, run_id: str, *, retryable: bool, code: str) -> None:
        self._check(principal, principal.tenant_id)
        safe_code = code if code in ("INVALID_EXECUTION_EVIDENCE", "EVIDENCE_COLLECTOR_UNAVAILABLE") else "INTERNAL_FAILURE"
        with self.engine.begin() as conn:
            conn.execute(update(_JOBS).where(
                _JOBS.c.tenant_id == principal.tenant_id, _JOBS.c.run_id == run_id,
                _JOBS.c.status == "RUNNING").values(
                    status="QUEUED" if retryable else "BLOCKED",
                    error_code=safe_code, lease_until=0))


class DurableEvaluationWorkflow:
    """Runnable processing hook; actual queue transport/scheduling owned by deployer."""

    def __init__(self, vault: DatasetVault, collector: EvidenceCollector,
                 jobs: SqlJobRepository, policy: EvaluationPolicy | None = None):
        self.vault = vault
        self.engine = EvaluationEngine(vault)
        self.collector = collector
        self.jobs = jobs
        self.policy = policy or EvaluationPolicy()

    def submit(self, principal: Principal, request: EvaluationRequest) -> EvaluationJob:
        self.vault.read(principal, request.dataset_version_ref)
        return self.jobs.submit(principal, request)

    def get(self, principal: Principal, run_id: str) -> EvaluationJob:
        return self.jobs.get(principal, run_id)

    def process(self, principal: Principal, run_id: str) -> EvaluationJob:
        request = self.jobs.claim(principal, run_id)
        if request is None:
            return self.jobs.get(principal, run_id)
        try:
            dataset = self.vault.read(principal, request.dataset_version_ref)
            evidence = tuple(self.collector.collect(request, PublicRunCase(c.case_id, c.input_ref))
                             for c in dataset.cases)
            for case, e in zip(dataset.cases, evidence):
                if not isinstance(e, EvidenceEnvelope) or (
                    e.tenant_id != request.tenant_id or
                    e.agent_spec_digest != request.agent_spec_digest or
                    e.dataset_version_ref != request.dataset_version_ref or
                    e.case_id != case.case_id or
                    e.observation.case_id != case.case_id or
                    not e.trace_ref
                ):
                    raise InvalidEvidence("untrusted candidate trace")
            result = self.engine.evaluate(principal, request,
                                          tuple(e.observation for e in evidence), self.policy)
            self.jobs.complete(principal, run_id, result)
        except (AccessDenied, InvalidEvidence):
            self.jobs.abort(principal, run_id, retryable=False,
                            code="INVALID_EXECUTION_EVIDENCE")
        except Exception:
            # Transient HTTP/provider failure, bounded by claim's max_attempts.
            self.jobs.abort(principal, run_id, retryable=True,
                            code="EVIDENCE_COLLECTOR_UNAVAILABLE")
        return self.jobs.get(principal, run_id)
