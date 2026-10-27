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
    estimated_usd: float = Field(default=0, ge=0, allow_inf_nan=False)

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
            old = self._effects.get(key)
            if old is None or old[0] != 'UNCERTAIN':
                raise RuntimeDenied('INVALID_EFFECT_TRANSITION')
            self._effects[key] = ('CONFIRMED', dict(result))

    def status(self, key: str) -> str | None:
        return self._effects.get(key, (None, None))[0]

def authorize_spec_for_runtime(spec: AgentSpec) -> None:
    """Runtime must enforce effect ceilings even if a trusted spec port is wrong."""
    for binding in spec.selected_tools:
        declared = set(binding.side_effects)
        if not declared or not declared <= {'read', 'draft_file'}:
            raise RuntimeDenied('EFFECT_POLICY_DENIED')


def validate_model_tool_args(args: object) -> None:
    """Reject non-JSON data, hidden credentials and excessively deep payloads.

    A schema-conformant JSON document is not necessarily safe to deliver to an
    external tool: credential-bearing nested keys are never model-authorized.
    """
    blocked = {'authorization', 'auth', 'secret', 'api_key', 'apikey',
               'password', 'access_token', 'refresh_token', 'private_key',
               'client_secret', 'x_api_key'}
    stack = [(args, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > 2048 or depth > 16:
            raise RuntimeDenied('INVALID_TOOL_ARGS')
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise RuntimeDenied('INVALID_TOOL_ARGS')
                if key.lower().replace('-', '_') in blocked:
                    raise RuntimeDenied('CREDENTIAL_IN_TOOL_ARGS')
                stack.append((child, depth + 1))
        elif isinstance(value, list):
            stack.extend((child, depth + 1) for child in value)
    try:
        encoded = json.dumps(args, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise RuntimeDenied('INVALID_TOOL_ARGS') from exc
    if len(encoded.encode('utf-8')) > 16000:
        raise RuntimeDenied('INVALID_TOOL_ARGS')


class ToolGateway:
    verified = False  # unverified fake port, denied by Runtime

    def __init__(self, tools: ToolPort, ledger: EffectLedger, *, timeout_seconds: float = 15.0):
        if not 0.01 <= timeout_seconds <= 60:
            raise ValueError('tool timeout outside configured safety limits')
        self.tools, self.ledger = tools, ledger
        self.timeout_seconds = timeout_seconds

    async def execute(self, spec: AgentSpec, binding: ToolBinding, *, args: dict,
                      run_id: str, step: int) -> tuple[dict, str]:
        authorize_spec_for_runtime(spec)
        if binding not in spec.selected_tools:
            raise RuntimeDenied('TOOL_DENIED')
        if not isinstance(args, dict):
            raise RuntimeDenied('INVALID_TOOL_ARGS')
        validate_model_tool_args(args)
        effect = any(e not in ('read',) for e in binding.side_effects)
        # Reserve one stable effect slot per ReAct step. Never key by model-supplied
        # args or tool choice: both may drift on resume after an uncertain commit.
        key = digest({'tenant': spec.tenant_id, 'agent': spec.agent_id,
                      'run': run_id, 'step': step})
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

class RunStorePort(Protocol):
    def load(self, tenant: str, run_id: str) -> tuple[str, RunResult] | None: ...
    def save(self, tenant: str, run_id: str, request_hash: str, result: RunResult) -> None: ...


class Runtime:
    def __init__(self, model: ModelPort, gateway: ToolGateway,
                 memory: ThreadMemory | None = None, *,
                 approved_spec_digests: frozenset[str] = frozenset(),
                 model_timeout_seconds: float = 30.0, run_store: RunStorePort | None = None):
        if not 0.01 <= model_timeout_seconds <= 120:
            raise ValueError('model timeout outside configured safety limits')
        self.model_timeout_seconds = model_timeout_seconds
        self.model, self.gateway = model, gateway
        self.run_store = run_store
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
        authorize_spec_for_runtime(spec)
        if getattr(self.model, 'tenant_id', tenant_id) != tenant_id:
            raise RuntimeDenied('MODEL_TENANT_DENIED')
        request_hash = digest({'agent': spec.artifact_digest, 'thread': thread_id, 'request': request})
        ident = (tenant_id, run_id)
        async with self._lock:
            cached = self._runs.get(ident)
            if cached is None and self.run_store is not None:
                cached = self.run_store.load(tenant_id, run_id)
            if cached is not None:
                old_hash, old_result = cached
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
                    try:
                        decision = await asyncio.wait_for(self.model.decide(route=spec.model_route,
                            prompt=spec.system_prompt, history=list(history),
                            tool_ids=tuple(tool_bindings), trace_id=trace_id),
                            timeout=self.model_timeout_seconds)
                    except TimeoutError as exc:
                        raise RuntimeDenied('MODEL_TIMEOUT') from exc
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
            if self.run_store is not None:
                self.run_store.save(tenant_id, run_id, request_hash, result)
            self._runs[ident] = (request_hash, result)
            return result
