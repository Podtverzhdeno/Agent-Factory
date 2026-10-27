"""Typed contract-first build handler. Not an approved HTTP service."""

from __future__ import annotations

import asyncio
import time
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .audit import audit_event
from .core import AgentSpec, BuildCommand, Builder, BuildError, TaskSnapshot, digest


class TaskPort(Protocol):
    def ready_snapshot(self, tenant_id: str, snapshot_id: str) -> TaskSnapshot | None: ...

class AgentSpecPort(Protocol):
    def put_if_absent(self, spec: AgentSpec) -> str: ...
    def get(self, tenant_id: str, spec_ref: str) -> AgentSpec | None: ...

class BuildResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    build_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    task_snapshot_id: str
    status: Literal['ASSEMBLED', 'BLOCKED']
    agent_spec_ref: str | None = None
    agent_spec_digest: str | None = None
    error_code: str | None = None

class InMemoryAgentSpecStore:
    """Immutable synthetic store. Tenant authentication is responsibility of adapter."""
    def __init__(self):
        self._values: dict[tuple[str, str], AgentSpec] = {}

    def put_if_absent(self, spec: AgentSpec) -> str:
        if not spec.verify_digest():
            raise BuildError('SPEC_TAMPERED', 'invalid artifact digest')
        ref = f'artifact://agent-specs/{spec.tenant_id}/{spec.agent_id}/{spec.agent_spec_version}'
        key = (spec.tenant_id, ref)
        old = self._values.get(key)
        if old is not None and old != spec:
            raise BuildError('SPEC_IMMUTABILITY_CONFLICT', 'same version with different contents')
        self._values[key] = spec
        return ref

    def get(self, tenant_id: str, spec_ref: str) -> AgentSpec | None:
        return self._values.get((tenant_id, spec_ref))

class BuildHandler:
    """Idempotency is local-only; production requires persistent unique index."""
    def __init__(self, builder: Builder, tasks: TaskPort, specs: AgentSpecPort):
        self.builder, self.tasks, self.specs = builder, tasks, specs
        self._operations: dict[tuple[str, str], tuple[str, BuildResult]] = {}
        self._lock = asyncio.Lock()

    async def build(self, command: BuildCommand) -> BuildResult:
        """Emit bounded audit records without recording objective or command contents."""
        started = time.monotonic()
        operation_id = command.build_id
        tenant_id = command.tenant_id
        audit_event("builder", "build.started", "STARTED",
                    tenant_id=tenant_id, operation_id=operation_id)
        try:
            result = await self._build_impl(command)
        except BuildError as exc:
            audit_event("builder", "build.denied", "DENIED",
                        tenant_id=tenant_id, operation_id=operation_id,
                        code=exc.code,
                        duration_ms=max(0, int((time.monotonic() - started) * 1000)))
            raise
        except Exception:  # noqa: BLE001 - sanitize unexpected failure before re-raising.
            audit_event("builder", "build.denied", "FAILED",
                        tenant_id=tenant_id, operation_id=operation_id,
                        code="UNEXPECTED_BUILD_EXCEPTION")
            raise
        audit_event("builder", "build.finished", result.status,
                    tenant_id=tenant_id, operation_id=operation_id,
                    code=result.error_code,
                    duration_ms=max(0, int((time.monotonic() - started) * 1000)))
        return result

    async def _build_impl(self, command: BuildCommand) -> BuildResult:
        if not command.idempotency_key:
            raise BuildError('MISSING_IDEMPOTENCY_KEY', 'command must have a key')
        payload_digest = digest(command.model_dump(mode='json'))
        key = (command.tenant_id, command.idempotency_key)
        async with self._lock:
            cached = self._operations.get(key)
            if cached is not None:
                if cached[0] != payload_digest:
                    raise BuildError('BUILD_IDEMPOTENCY_CONFLICT', 'key reused with different command')
                audit_event('builder', 'build.replayed', 'REPLAYED',
                            tenant_id=command.tenant_id, operation_id=command.build_id)
                return cached[1]
            snapshot = self.tasks.ready_snapshot(command.tenant_id, command.task_snapshot_id)
            if snapshot is None:
                result = BuildResult(build_id=command.build_id, tenant_id=command.tenant_id,
                    task_snapshot_id=command.task_snapshot_id, status='BLOCKED',
                    error_code='SNAPSHOT_NOT_READY_OR_DENIED')
            else:
                try:
                    spec = self.builder.assemble(snapshot, command)
                    ref = self.specs.put_if_absent(spec)
                    result = BuildResult(build_id=command.build_id, tenant_id=command.tenant_id,
                        task_snapshot_id=command.task_snapshot_id, status='ASSEMBLED',
                        agent_spec_ref=ref, agent_spec_digest=spec.artifact_digest)
                except BuildError as exc:
                    result = BuildResult(build_id=command.build_id, tenant_id=command.tenant_id,
                        task_snapshot_id=command.task_snapshot_id, status='BLOCKED',
                        error_code=exc.code)
            self._operations[key] = (payload_digest, result)
            return result
