"""Graph contract/idempotency proof with fake compiled-graph port (not SDK)."""
import pytest
from agent_runtime.langgraph_adapter import invoke_graph

from agent_runtime import (
    Decision,
    EffectLedger,
    Runtime,
    RuntimeDenied,
    SqliteRunStore,
    ToolPolicy,
    VerifiedToolGateway,
)
from test_engine import build, FakeTools, manifest, Registry, ScriptedModel, task


def setup_runtime(tmp_path):
    spec = build(task('rfq', ['read'], ['read'], ['read']),
                 Registry([manifest('catalog', ['read'], ['read'], ['read'])]))
    binding = spec.selected_tools[0]
    gateway = VerifiedToolGateway(FakeTools(), EffectLedger(), policies={'catalog': ToolPolicy(
        tenant_id='buyer', tool_id='catalog', version=binding.version,
        manifest_digest=binding.digest, scopes=frozenset(binding.granted_scopes),
        effect_mode='read', input_schema={'type': 'object'}, output_schema={'type': 'object'})})
    runtime = Runtime(ScriptedModel([Decision(kind='final', text='ok')]), gateway,
                      approved_spec_digests=frozenset({spec.artifact_digest}),
                      run_store=SqliteRunStore(tmp_path / 'runs.sqlite'))
    return spec, runtime


class FakeCompiledGraph:
    def __init__(self):
        self.calls = 0

    async def ainvoke(self, state, config):
        self.calls += 1
        return {'result': {'status': 'COMPLETED', 'run_id': state['run_id'],
                'trace_id': state['trace_id'], 'answer': 'synthetic result',
                'tool_effect_refs': ('artifact://fake/effect',),
                'cost_usd': 0.1, 'steps': 1, 'error_code': None}}


@pytest.mark.asyncio
async def test_graph_result_loaded_without_replaying_graph(tmp_path):
    spec, runtime = setup_runtime(tmp_path)
    graph = FakeCompiledGraph()
    kw = dict(tenant_id='buyer', thread_id='thread', run_id='run-001',
              request='read', trace_id='tr-1')
    original = await invoke_graph(graph, runtime, spec, **kw)
    assert graph.calls == 1
    spec2, runtime2 = setup_runtime(tmp_path)
    assert spec2 == spec
    restored = await invoke_graph(graph, runtime2, spec2, **{**kw, 'trace_id': 'tr-2'})
    assert restored == original
    assert graph.calls == 1
    with pytest.raises(RuntimeDenied, match='RUN_IDEMPOTENCY_CONFLICT'):
        await invoke_graph(graph, runtime2, spec2, **{**kw, 'request': 'changed'})
    assert graph.calls == 1


@pytest.mark.asyncio
async def test_graph_invalid_run_denied_before_execution(tmp_path):
    spec, runtime = setup_runtime(tmp_path)
    graph = FakeCompiledGraph()
    with pytest.raises(RuntimeDenied, match='INVALID_RUN_INPUT'):
        await invoke_graph(graph, runtime, spec, tenant_id='buyer', thread_id='thread',
                           run_id='', request='read', trace_id='tr-1')
    assert graph.calls == 0
