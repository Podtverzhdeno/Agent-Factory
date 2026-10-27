"""Durable, tenant-scoped evaluation jobs and transactional completion outbox.

PostgreSQL-compatible SQLAlchemy Core. Schema creation belongs to migrations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column, Float, ForeignKeyConstraint, Integer, MetaData, String, Table,
    Text, UniqueConstraint, and_, or_, select, update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .evaluation import EvaluationRequest, EvaluationResult
from .primitives import AccessDenied, InvalidEvidence, Principal

metadata = MetaData()
jobs = Table(
    "evaluation_jobs", metadata,
    Column("tenant_id", String(200), primary_key=True),
    Column("run_id", String(200), primary_key=True),
    Column("idempotency_key", String(200), nullable=False),
    Column("request_json", Text, nullable=False),
    Column("status", String(32), nullable=False),
    Column("lease_owner", String(200)),
    Column("lease_until", Float),
    Column("attempt", Integer, nullable=False, default=0),
    Column("result_json", Text),
    Column("error_code", String(100)),
    UniqueConstraint("tenant_id", "idempotency_key", name="unique_tenant_eval_idem"),
)
outbox = Table(
    "evaluation_outbox", metadata,
    Column("event_id", String(36), primary_key=True),
    Column("tenant_id", String(200), nullable=False),
    Column("run_id", String(200), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("dispatched", Integer, nullable=False, default=0),
    ForeignKeyConstraint(["tenant_id", "run_id"], ["evaluation_jobs.tenant_id", "evaluation_jobs.run_id"]),
)


@dataclass(frozen=True)
class JobRecord:
    tenant_id: str
    run_id: str
    status: str
    attempt: int
    result: dict[str, Any] | None
    error_code: str | None


@dataclass(frozen=True)
class Claim:
    request: EvaluationRequest
    run_id: str
    worker_id: str
    attempt: int


@dataclass(frozen=True)
class OutboxRecord:
    event_id: str
    tenant_id: str
    run_id: str
    payload: dict[str, Any]


def _check(principal: Principal, tenant_id: str) -> None:
    if principal.role != "evaluation" or principal.tenant_id != tenant_id:
        raise AccessDenied("trusted tenant evaluator identity required")


def _json(value: Any) -> str:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


class SqlEvaluationJobStore:
    """DB-atomic job claims, lease fencing and transactionally persisted events."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def submit(self, principal: Principal, request: EvaluationRequest) -> JobRecord:
        _check(principal, request.tenant_id)
        if not all((request.tenant_id, request.agent_spec_ref, request.agent_spec_digest,
                    request.dataset_version_ref, request.policy_ref,
                    request.idempotency_key, request.evaluation_run_id)):
            raise InvalidEvidence("pinned request fields mandatory")
        encoded = _json(asdict(request))
        try:
            with self.engine.begin() as conn:
                conn.execute(jobs.insert().values(
                    tenant_id=request.tenant_id, run_id=request.evaluation_run_id,
                    idempotency_key=request.idempotency_key, request_json=encoded,
                    status="QUEUED", attempt=0,
                ))
            return self.get(principal, request.evaluation_run_id)
        except IntegrityError:
            with self.engine.connect() as conn:
                row = conn.execute(select(jobs).where(and_(
                    jobs.c.tenant_id == request.tenant_id,
                    jobs.c.idempotency_key == request.idempotency_key,
                ))).mappings().first()
            if row is None or row["request_json"] != encoded:
                raise InvalidEvidence("idempotency key/run ID conflict") from None
            return self.get(principal, row["run_id"])

    def get(self, principal: Principal, run_id: str) -> JobRecord:
        _check(principal, principal.tenant_id)
        with self.engine.connect() as conn:
            row = conn.execute(select(jobs).where(and_(
                jobs.c.tenant_id == principal.tenant_id, jobs.c.run_id == run_id,
            ))).mappings().first()
        if row is None:
            raise KeyError("evaluation job unavailable")
        return JobRecord(principal.tenant_id, run_id, row["status"], row["attempt"],
                         json.loads(row["result_json"]) if row["result_json"] else None,
                         row["error_code"])

    def claim(self, principal: Principal, *, run_id: str, worker_id: str,
              now: float, lease_seconds: float = 30.0, max_attempts: int = 3) -> Claim | None:
        _check(principal, principal.tenant_id)
        if (not worker_id or not isfinite(now) or not isfinite(lease_seconds)
                or not 0 < lease_seconds <= 3600 or max_attempts < 1):
            raise ValueError("bounded worker lease required")
        with self.engine.begin() as conn:
            claimed = conn.execute(update(jobs).where(and_(
                jobs.c.tenant_id == principal.tenant_id, jobs.c.run_id == run_id,
                jobs.c.attempt < max_attempts,
                or_(jobs.c.status == "QUEUED",
                    and_(jobs.c.status == "RUNNING", jobs.c.lease_until <= now)),
            )).values(status="RUNNING", lease_owner=worker_id,
                      lease_until=now + lease_seconds, attempt=jobs.c.attempt + 1))
            if claimed.rowcount != 1:
                return None
            row = conn.execute(select(jobs).where(and_(
                jobs.c.tenant_id == principal.tenant_id, jobs.c.run_id == run_id,
            ))).mappings().one()
            return Claim(EvaluationRequest(**json.loads(row["request_json"])),
                         run_id, worker_id, row["attempt"])

    def complete(self, principal: Principal, claim: Claim, *, now: float,
                 status: str, result: EvaluationResult | None = None,
                 error_code: str | None = None) -> JobRecord:
        _check(principal, claim.request.tenant_id)
        if status not in ("PASSED", "FAILED", "BLOCKED"):
            raise InvalidEvidence("only terminal statuses may be committed")
        if status == "PASSED" and (result is None or not result.passed or result.hard_veto
                                    or not result.independent_acceptance or result.status != "PASSED"):
            raise InvalidEvidence("unverified quality result cannot be PASSED")
        if result is not None and (result.tenant_id != principal.tenant_id
                                    or result.evaluation_run_id != claim.run_id
                                    or result.agent_spec_digest != claim.request.agent_spec_digest
                                    or result.dataset_version_ref != claim.request.dataset_version_ref):
            raise InvalidEvidence("evaluation evidence mismatch")
        if error_code and (len(error_code) > 100 or not all(
            c.isascii() and (c.isupper() or c.isdigit() or c == "_") for c in error_code
        )):
            raise InvalidEvidence("error code must be enum-like and safe")
        if not isfinite(now):
            raise InvalidEvidence("finite commit time required")
        payload = {"schema_version": "0.1", "type": "evaluation.completed",
                   "occurred_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                   "correlation_id": claim.request.evaluation_run_id,
                   "event_id": str(uuid4()), "tenant_id": principal.tenant_id,
                   "run_id": claim.run_id, "status": status,
                   "passed": bool(result and result.passed and status == "PASSED"),
                   "hard_veto": bool(result and result.hard_veto),
                   "agent_spec_digest": claim.request.agent_spec_digest,
                   "dataset_version_ref": claim.request.dataset_version_ref}
        with self.engine.begin() as conn:
            updated = conn.execute(update(jobs).where(and_(
                jobs.c.tenant_id == principal.tenant_id,
                jobs.c.run_id == claim.run_id,
                jobs.c.status == "RUNNING", jobs.c.lease_owner == claim.worker_id,
                jobs.c.attempt == claim.attempt, jobs.c.lease_until > now,
            )).values(status=status, lease_owner=None, lease_until=None,
                      result_json=_json(asdict(result)) if result else None,
                      error_code=error_code))
            if updated.rowcount != 1:
                raise InvalidEvidence("stale claim / revoked lease")
            conn.execute(outbox.insert().values(
                event_id=payload["event_id"], tenant_id=principal.tenant_id,
                run_id=claim.run_id, payload_json=_json(payload), dispatched=0,
            ))
        return self.get(principal, claim.run_id)

    def pending_events(self, principal: Principal, limit: int = 100) -> tuple[OutboxRecord, ...]:
        _check(principal, principal.tenant_id)
        if not 1 <= limit <= 1000:
            raise ValueError("invalid outbox batch limit")
        with self.engine.connect() as conn:
            rows = conn.execute(select(outbox).where(and_(
                outbox.c.tenant_id == principal.tenant_id, outbox.c.dispatched == 0,
            )).order_by(outbox.c.event_id).limit(limit)).mappings().all()
        return tuple(OutboxRecord(row["event_id"], row["tenant_id"], row["run_id"],
                                  json.loads(row["payload_json"])) for row in rows)

    def mark_dispatched(self, principal: Principal, event_id: str) -> bool:
        _check(principal, principal.tenant_id)
        with self.engine.begin() as conn:
            updated = conn.execute(update(outbox).where(and_(
                outbox.c.tenant_id == principal.tenant_id,
                outbox.c.event_id == event_id, outbox.c.dispatched == 0,
            )).values(dispatched=1))
            return updated.rowcount == 1


    def block_exhausted(self, principal: Principal, *, now: float,
                        max_attempts: int = 3, limit: int = 100) -> int:
        """Fence exhausted leases and atomically publish BLOCKED status."""
        _check(principal, principal.tenant_id)
        if not isfinite(now) or max_attempts < 1 or not 1 <= limit <= 1000:
            raise ValueError("invalid reaper parameters")
        blocked = 0
        with self.engine.begin() as conn:
            stale = conn.execute(select(jobs).where(and_(
                jobs.c.tenant_id == principal.tenant_id,
                jobs.c.status == "RUNNING", jobs.c.lease_until <= now,
                jobs.c.attempt >= max_attempts,
            )).limit(limit)).mappings().all()
            for row in stale:
                updated = conn.execute(update(jobs).where(and_(
                    jobs.c.tenant_id == principal.tenant_id,
                    jobs.c.run_id == row["run_id"], jobs.c.status == "RUNNING",
                    jobs.c.attempt == row["attempt"], jobs.c.lease_until <= now,
                )).values(status="BLOCKED", lease_owner=None, lease_until=None,
                          error_code="MAX_ATTEMPTS_EXHAUSTED"))
                if updated.rowcount != 1:
                    continue
                request = EvaluationRequest(**json.loads(row["request_json"]))
                payload = {"schema_version": "0.1", "type": "evaluation.completed",
                           "event_id": str(uuid4()), "tenant_id": principal.tenant_id,
                           "correlation_id": request.evaluation_run_id,
                           "occurred_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                           "run_id": row["run_id"], "status": "BLOCKED",
                           "passed": False, "hard_veto": False,
                           "agent_spec_digest": request.agent_spec_digest,
                           "dataset_version_ref": request.dataset_version_ref}
                conn.execute(outbox.insert().values(
                    event_id=payload["event_id"], tenant_id=principal.tenant_id,
                    run_id=row["run_id"], payload_json=_json(payload), dispatched=0))
                blocked += 1
        return blocked
