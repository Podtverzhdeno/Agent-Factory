"""LangGraph ReAct-style candidate harness; Postgres saver is a swappable adapter."""
from __future__ import annotations
import asyncio
import json
from typing import Any, TypedDict
from .core import RunResult, RuntimeDenied, authorize_spec_for_runtime
from agent_builder import digest

class GraphState(TypedDict, total=False):
    tenant_id: str
    run_id: str
    thread_id: str
    request: str
    trace_id: str
    history: list[dict[str, Any]]
    steps: int
    cost_usd: float
    effects: list[str]
    pending_tool: str
    pending_args: dict
    terminal_error: str | None
    answer: str
    result: dict

def build_graph(runtime, spec, checkpointer=None):
    """Construct LangGraph decide→tool→decide; caller must pass tenant-bound thread ID.

    Tool ledger must be transactionally durable separately from the graph checkpoint.
    """
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError as exc:
        raise RuntimeError('Install langgraph to compile the execution graph') from exc

    async def decide(state: GraphState) -> dict:
        if state['tenant_id'] != spec.tenant_id or not spec.verify_digest():
            return {'terminal_error': 'SPEC_OR_TENANT_DENIED'}
        if spec.artifact_digest not in runtime.approved_spec_digests:
            return {'terminal_error': 'SPEC_NOT_PINNED'}
        if not getattr(runtime.gateway, 'verified', False):
            return {'terminal_error': 'UNVERIFIED_TOOL_GATEWAY'}
        try:
            authorize_spec_for_runtime(spec)
        except RuntimeDenied as exc:
            return {'terminal_error': exc.code}
        if getattr(runtime.model, 'tenant_id', spec.tenant_id) != spec.tenant_id:
            return {'terminal_error': 'MODEL_TENANT_DENIED'}
        step = state.get('steps', 0) + 1
        if step > spec.limits.max_steps:
            return {'steps': step, 'terminal_error': 'MAX_STEPS_EXCEEDED'}
        history = state.get('history')
        if history is None:
            history = runtime.memory.get(spec.tenant_id, spec.agent_id, state['thread_id'])
            history.append({'role': 'user', 'content': state['request']})
        try:
            d = await asyncio.wait_for(runtime.model.decide(
                route=spec.model_route, prompt=spec.system_prompt, history=list(history),
                tool_ids=tuple(b.tool_id for b in spec.selected_tools),
                trace_id=state['trace_id']), timeout=runtime.model_timeout_seconds)
            cost = state.get('cost_usd', 0) + d.estimated_usd
            if cost > spec.limits.max_usd_per_run:
                raise RuntimeDenied('BUDGET_EXCEEDED')
            if d.kind == 'final':
                if not d.text:
                    raise RuntimeDenied('EMPTY_RESPONSE')
                return {'steps': step, 'cost_usd': cost, 'history': history,
                        'answer': d.text, 'terminal_error': None, 'pending_tool': ''}
            if d.tool_id not in {b.tool_id for b in spec.selected_tools}:
                raise RuntimeDenied('TOOL_DENIED')
            return {'steps': step, 'cost_usd': cost, 'history': history,
                    'pending_tool': d.tool_id, 'pending_args': d.args,
                    'terminal_error': None}
        except TimeoutError:
            return {'steps': step, 'history': history, 'terminal_error': 'MODEL_TIMEOUT',
                    'pending_tool': ''}
        except RuntimeDenied as exc:
            return {'steps': step, 'history': history, 'terminal_error': exc.code, 'pending_tool': ''}
        except Exception:
            return {'steps': step, 'history': history, 'terminal_error': 'MODEL_UNAVAILABLE', 'pending_tool': ''}

    def route_after_decide(state: GraphState) -> str:
        return 'finish' if state.get('terminal_error') or not state.get('pending_tool') else 'tool'

    async def tool(state: GraphState) -> dict:
        binding = next((b for b in spec.selected_tools if b.tool_id == state['pending_tool']), None)
        if binding is None:
            return {'terminal_error': 'TOOL_DENIED', 'pending_tool': ''}
        try:
            value, effect = await runtime.gateway.execute(spec, binding,
                args=state.get('pending_args', {}), run_id=state['run_id'], step=state['steps'])
            history = state['history'] + [{'role': 'tool', 'name': binding.tool_id,
                                            'content': json.dumps(value)[:8000]}]
            return {'history': history, 'effects': state.get('effects', []) + [effect],
                    'pending_tool': ''}
        except RuntimeDenied as exc:
            return {'terminal_error': exc.code, 'pending_tool': ''}
        except Exception:
            return {'terminal_error': 'EXECUTION_UNCERTAIN', 'pending_tool': ''}

    def route_after_tool(state: GraphState) -> str:
        return 'finish' if state.get('terminal_error') else 'decide'

    async def finish(state: GraphState) -> dict:
        code = state.get('terminal_error')
        if not code:
            runtime.memory.append(spec.tenant_id, spec.agent_id, state['thread_id'],
                                  {'role': 'user', 'content': state['request']})
            runtime.memory.append(spec.tenant_id, spec.agent_id, state['thread_id'],
                                  {'role': 'assistant', 'content': state['answer']})
        result = RunResult(status='BLOCKED' if code else 'COMPLETED',
            run_id=state['run_id'], trace_id=state['trace_id'], answer='' if code else state.get('answer', ''),
            tool_effect_refs=tuple(state.get('effects', [])),
            cost_usd=state.get('cost_usd', 0), steps=state.get('steps', 0), error_code=code)
        return {'result': result.__dict__}

    graph = StateGraph(GraphState)
    graph.add_node('decide', decide)
    graph.add_node('tool', tool)
    graph.add_node('finish', finish)
    graph.add_edge(START, 'decide')
    graph.add_conditional_edges('decide', route_after_decide, {'tool': 'tool', 'finish': 'finish'})
    graph.add_conditional_edges('tool', route_after_tool, {'decide': 'decide', 'finish': 'finish'})
    graph.add_edge('finish', END)
    return graph.compile(checkpointer=checkpointer)

def postgres_checkpointer(uri: str):
    """Official LangGraph async context manager; caller does saver.setup() and TLS provisioning."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    return AsyncPostgresSaver.from_conn_string(uri)

async def invoke_graph(graph, runtime, spec, *, tenant_id: str, thread_id: str,
                       run_id: str, request: str, trace_id: str) -> dict:
    """Bind checkpoint identity to tenant, agent and version, never raw user thread.

    This does not provide exactly-once effects; an independent durable effect
    ledger and business-side reconciliation remain mandatory.
    """
    if tenant_id != spec.tenant_id or not spec.verify_digest():
        raise RuntimeDenied('SPEC_OR_TENANT_DENIED')
    if spec.artifact_digest not in runtime.approved_spec_digests:
        raise RuntimeDenied('SPEC_NOT_PINNED')
    if not getattr(runtime.gateway, 'verified', False):
        raise RuntimeDenied('UNVERIFIED_TOOL_GATEWAY')
    authorize_spec_for_runtime(spec)
    if getattr(runtime.model, 'tenant_id', tenant_id) != tenant_id:
        raise RuntimeDenied('MODEL_TENANT_DENIED')
    if (not run_id or not thread_id or not trace_id or len(trace_id) > 128
            or not request or len(request) > 20000):
        raise RuntimeDenied('INVALID_RUN_INPUT')
    request_hash = digest({'agent': spec.artifact_digest, 'thread': thread_id,
                           'request': request})
    # The lock protects local workers; the durable store must enforce uniqueness
    # across processes. External effects use a separate reservation ledger.
    async with runtime._lock:
        if runtime.run_store is not None:
            previous = runtime.run_store.load(tenant_id, run_id)
            if previous is not None:
                old_hash, old_result = previous
                if old_hash != request_hash:
                    raise RuntimeDenied('RUN_IDEMPOTENCY_CONFLICT')
                return asdict(old_result)
        checkpoint_id = digest({'tenant': tenant_id, 'agent': spec.agent_id,
                                'version': spec.agent_spec_version, 'thread': thread_id})
        history = runtime.memory.get(tenant_id, spec.agent_id, thread_id)
        history.append({'role': 'user', 'content': request})
        state = {'tenant_id': tenant_id, 'thread_id': thread_id, 'run_id': run_id,
                 'request': request, 'trace_id': trace_id, 'history': history,
                 'steps': 0, 'cost_usd': 0.0, 'effects': [], 'pending_tool': '',
                 'pending_args': {}, 'terminal_error': None, 'answer': '', 'result': {}}
        final = await graph.ainvoke(
            state, config={'configurable': {'thread_id': checkpoint_id}})
        if not isinstance(final, dict) or not isinstance(final.get('result'), dict):
            raise RuntimeDenied('INVALID_GRAPH_RESULT')
        if runtime.run_store is not None:
            run_result = RunResult(**final['result'])
            if run_result.status not in ('COMPLETED', 'BLOCKED') or run_result.run_id != run_id:
                raise RuntimeDenied('INVALID_GRAPH_RESULT')
            runtime.run_store.save(tenant_id, run_id, request_hash, run_result)
        return final['result']
