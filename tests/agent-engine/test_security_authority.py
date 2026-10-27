"""Defence in depth: never infer authority from a pinned specification."""
import pytest
from agent_builder import digest
from agent_runtime import Decision, EffectLedger, Runtime, RuntimeDenied, ToolPolicy, VerifiedToolGateway
from agent_runtime.langgraph_adapter import invoke_graph
from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task


def fixture():
    spec = build(task('read', ['read'], ['read'], ['read']),
                 Registry([manifest('read.tool', ['read'], ['read'], ['read'])]))
    b = spec.selected_tools[0]
    tools = FakeTools()
    gateway = VerifiedToolGateway(tools, EffectLedger(), policies={'read.tool': ToolPolicy(
        tenant_id='buyer', tool_id=b.tool_id, version=b.version, manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes), input_schema={'type': 'object'},
        output_schema={'type': 'object'}, effect_mode='read')})
    return spec, gateway, tools


@pytest.mark.asyncio
async def test_pinned_spec_with_payment_effect_blocked_at_runtime():
    spec, gateway, tools = fixture()
    original = spec.selected_tools[0]
    forged_binding = original.model_copy(update={'side_effects': ('payment',)})
    forged = spec.model_copy(update={'selected_tools': (forged_binding,)})
    forged = forged.model_copy(update={'artifact_digest': digest(
        forged.model_dump(exclude={'artifact_digest'}, mode='json'))})
    runtime = Runtime(ScriptedModel([Decision(kind='final', text='should never run')]),
                      gateway, approved_spec_digests=frozenset({forged.artifact_digest}))
    with pytest.raises(RuntimeDenied, match='EFFECT_POLICY_DENIED'):
        await runtime.run(forged, tenant_id='buyer', run_id='r', thread_id='t',
                          request='read', trace_id='tr')
    assert tools.called == []


@pytest.mark.asyncio
async def test_model_tenant_mismatch_denied_before_inference():
    spec, gateway, tools = fixture()
    model = ScriptedModel([Decision(kind='final', text='must not run')])
    model.tenant_id = 'seller'
    runtime = Runtime(model, gateway, approved_spec_digests=frozenset({spec.artifact_digest}))
    with pytest.raises(RuntimeDenied, match='MODEL_TENANT_DENIED'):
        await runtime.run(spec, tenant_id='buyer', run_id='r', thread_id='t',
                          request='read', trace_id='tr')
    assert len(model.decisions) == 1

    class FakeGraph:
        async def ainvoke(self, state, config):
            raise AssertionError('graph should never execute')

    with pytest.raises(RuntimeDenied, match='MODEL_TENANT_DENIED'):
        await invoke_graph(FakeGraph(), runtime, spec, tenant_id='buyer',
                           run_id='r', thread_id='t', request='read', trace_id='tr')
