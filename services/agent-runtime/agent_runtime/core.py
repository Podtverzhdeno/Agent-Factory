"""Sandbox candidate runtime. No auto-release, external network or implicit grants."""
from __future__ import annotations
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol
from agent_builder import AgentSpec, ToolBinding, digest
from pydantic import BaseModel, ConfigDict, Field, model_validator

class RuntimeDenied(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['tool', 'final']
    tool_id: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    text: str = ''
    source_refs: tuple[str, ...] = ()
    estimated_usd: float = Field(default=0, ge=0)

    @model_validator(mode='after')
    def consistent_action(self):
        if self.kind == 'tool' and (not self.tool_id or self.text):
            raise ValueError('tool action requires tool_id and no final text')
        if self.kind == 'final' and (self.tool_id is not None or self.args):
            raise ValueError('final answer cannot request tool execution')
        return self

class ModelPort(Protocol):
    async def decide(self, *, route: str, prompt: str, history: list[dict],
                     tool_ids: tuple[str, ...], trace_id: str) -> Decision: ...

class ToolPort(Protocol):
    async def call(self, *, tenant_id: str, tool_id: str, args: dict,
                   idempotency_key: str) -> dict: ...

class ThreadMemory:
    def __init__(self):
        self._threads: dict[tuple[str, str, str], list[dict]] = {}

    def get(self, tenant: str, agent: str, thread: str) -> list[dict]:
        return list(self._threads.get((tenant, agent, thread), [])[-50:])

    def append(self, tenant: str, agent: str, thread: str, entry: dict) -> None:
        if len(json.dumps(entry)) > 16000:
            raise RuntimeDenied('MEMORY_TOO_LARGE')
        values = self._threads.setdefault((tenant, agent, thread), [])
        values.append(dict(entry))
        if len(values) > 100:
            del values[:-100]

class LongTermMemory:
    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._items: dict[tuple[str, str, str], tuple[float, str]] = {}

    def put(self, tenant: str, agent: str, key: str, text: str, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0 or len(text) > 10000:
            raise RuntimeDenied('MEMORY_POLICY_DENIED')
        self._items[(tenant, agent, key)] = (self._clock() + ttl_seconds, text)

    def get(self, tenant: str, agent: str, key: str) -> str | None:
        item = self._items.get((tenant, agent, key))
        return item[1] if item and item[0] > self._clock() else None

class EffectLedger:
    """In-memory fake, NOT crash-durable. Reserve BEFORE call, deny retry if uncertain."""
    def __init__(self):
        self._effects: dict[str, tuple[str, dict | None]] = {}
        self._lock = asyncio.Lock()

    async def reserve(self, key: str) -> None:
        async with self._lock:
            if key in self._effects:
                raise RuntimeDenied('EFFECT_REPLAY_REQUIRES_RECONCILIATION')
            self._effects[key] = ('UNCERTAIN', None)

    async def finish(self, key: str, result: dict) -> None:
        async with self._lock:
            self._effects[key] = ('CONFIRMED', dict(result))

    def status(self, key: str) -> str | None:
        return self._effects.get(key, (None, None))[0]

class ToolGateway:
    verified = False  # unverified fake port, denied by Runtime

    def __init__(self, tools: ToolPort, ledger: EffectLedger, *, timeout_seconds: float = 15.0):
        if not 0.01 <= timeout_seconds <= 60:
            raise ValueError('tool timeout outside configured safety limits')
        self.tools, self.ledger = tools, ledger
        self.timeout_seconds = timeout_seconds

    async def execute(self, spec: AgentSpec, binding: ToolBinding, *, args: dict,
                      run_id: str, step: int) -> tuple[dict, str]:
        if binding not in spec.selected_tools:
            raise RuntimeDenied('TOOL_DENIED')
        if not isinstance(args, dict) or len(json.dumps(args)) > 16000:
            raise RuntimeDenied('INVALID_TOOL_ARGS')
        if any(k.lower() in ('auth', 'secret', 'api_key', 'password') for k in args):
            raise RuntimeDenied('CREDENTIAL_IN_TOOL_ARGS')
        effect = any(e not in ('read',) for e in binding.side_effects)
        key = digest({'tenant': spec.tenant_id, 'agent': spec.agent_id,
                      'run': run_id, 'step': step, 'tool': binding.tool_id, 'args': args})
        if effect:
            await self.ledger.reserve(key)
        try:
            result = await asyncio.wait_for(self.tools.call(tenant_id=spec.tenant_id,
                tool_id=binding.tool_id, args=args, idempotency_key=key),
                timeout=self.timeout_seconds)
        except TimeoutError as exc:
            raise RuntimeDenied('TOOL_TIMEOUT_UNCERTAIN') from exc
        if not isinstance(result, dict):
            raise RuntimeDenied('INVALID_TOOL_RESULT')
        if effect:
            await self.ledger.finish(key, result)
        return result, key

@dataclass(frozen=True)
class RunResult:
    status: Literal['COMPLETED', 'BLOCKED']
    run_id: str
    trace_id: str
    answer: str
    tool_effect_refs: tuple[str, ...]
    cost_usd: float
    steps: int
    error_code: str | None = None

class Runtime:
    def __init__(self, model: ModelPort, gateway: ToolGateway,
                 memory: ThreadMemory | None = None, *,
                 approved_spec_digests: frozenset[str] = frozenset()):
        self.model, self.gateway = model, gateway
        self.memory = memory or ThreadMemory()
        self.approved_spec_digests = approved_spec_digests
        self._runs: dict[tuple[str, str], tuple[str, RunResult]] = {}
        self._lock = asyncio.Lock()

    async def run(self, spec: AgentSpec, *, tenant_id: str, run_id: str,
                  thread_id: str, request: str, trace_id: str) -> RunResult:
        if tenant_id != spec.tenant_id:
            raise RuntimeDenied('TENANT_DENIED')
        if (not run_id or not thread_id or not trace_id or len(trace_id) > 128
                or not request or len(request) > 20000):
            raise RuntimeDenied('INVALID_RUN_INPUT')
        if not spec.verify_digest():
            raise RuntimeDenied('SPEC_TAMPERED')
        if spec.artifact_digest not in self.approved_spec_digests:
            raise RuntimeDenied('SPEC_NOT_PINNED')
        if not getattr(self.gateway, 'verified', False):
            raise RuntimeDenied('UNVERIFIED_TOOL_GATEWAY')
        request_hash = digest({'agent': spec.artifact_digest, 'thread': thread_id, 'request': request})
        ident = (tenant_id, run_id)
        async with self._lock:
            if ident in self._runs:
                old_hash, old_result = self._runs[ident]
                if old_hash != request_hash:
                    raise RuntimeDenied('RUN_IDEMPOTENCY_CONFLICT')
                return old_result
            history = self.memory.get(tenant_id, spec.agent_id, thread_id)
            history.append({'role': 'user', 'content': request})
            effects: list[str] = []
            spent, step, answer, code = 0.0, 0, '', None
            tool_bindings = {b.tool_id: b for b in spec.selected_tools}
            try:
                while step < spec.limits.max_steps:
                    step += 1
                    decision = await self.model.decide(route=spec.model_route,
                        prompt=spec.system_prompt, history=list(history),
                        tool_ids=tuple(tool_bindings), trace_id=trace_id)
                    spent += decision.estimated_usd
                    if spent > spec.limits.max_usd_per_run:
                        raise RuntimeDenied('BUDGET_EXCEEDED')
                    if decision.kind == 'final':
                        answer = decision.text
                        if not answer:
                            raise RuntimeDenied('EMPTY_RESPONSE')
                        break
                    binding = tool_bindings.get(decision.tool_id or '')
                    if binding is None:
                        raise RuntimeDenied('TOOL_DENIED')
                    result, effect_ref = await self.gateway.execute(spec, binding,
                        args=decision.args, run_id=run_id, step=step)
                    effects.append(effect_ref)
                    history.append({'role': 'tool', 'name': binding.tool_id,
                                    'content': json.dumps(result, ensure_ascii=False)[:8000]})
                else:
                    raise RuntimeDenied('MAX_STEPS_EXCEEDED')
            except RuntimeDenied as exc:
                code = exc.code
            except Exception:
                code = 'EXECUTION_UNCERTAIN'
            if code is None:
                self.memory.append(tenant_id, spec.agent_id, thread_id,
                                   {'role': 'user', 'content': request})
                self.memory.append(tenant_id, spec.agent_id, thread_id,
                                   {'role': 'assistant', 'content': answer})
            result = RunResult(status='BLOCKED' if code else 'COMPLETED',
                run_id=run_id, trace_id=trace_id, answer=answer if not code else '',
                tool_effect_refs=tuple(effects), cost_usd=spent, steps=step, error_code=code)
            self._runs[ident] = (request_hash, result)
            return result
