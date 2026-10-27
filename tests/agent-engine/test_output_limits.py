"""Read and draft tools must not propagate oversized/unserializable evidence."""
import pytest
from agent_runtime import EffectLedger, RuntimeDenied, ToolPolicy, VerifiedToolGateway
from test_engine import Registry, build, manifest, task


class OversizedOutputPort:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    async def call(self, **kwargs):
        self.calls += 1
        return {'text': self.value}


@pytest.mark.asyncio
@pytest.mark.parametrize('effect,scopes', [('read', ['read']), ('draft_file', ['draft:write'])])
async def test_large_output_denied_before_confirmation(effect, scopes):
    spec = build(task('oversized', ['render'], [effect], scopes),
                 Registry([manifest('render', ['render'], [effect], scopes)]))
    binding = spec.selected_tools[0]
    policy = ToolPolicy(tenant_id=spec.tenant_id, tool_id=binding.tool_id,
        version=binding.version, manifest_digest=binding.digest,
        scopes=frozenset(binding.granted_scopes), effect_mode=effect,
        input_schema={'type':'object'},output_schema={'type':'object'})
    port = OversizedOutputPort('💣' * 16000)
    ledger = EffectLedger()
    gateway = VerifiedToolGateway(port, ledger, policies={'render':policy})
    with pytest.raises(RuntimeDenied, match='TOOL_OUTPUT_TOO_LARGE'):
        await gateway.execute(spec, binding, args={}, run_id='run', step=1)
    assert port.calls == 1
    if effect == 'draft_file':
        with pytest.raises(RuntimeDenied, match='EFFECT_REPLAY_REQUIRES_RECONCILIATION'):
            await gateway.execute(spec, binding, args={}, run_id='run', step=1)
        assert port.calls == 1


@pytest.mark.asyncio
async def test_recursive_tool_output_is_denied():
    spec = build(task('render', ['render'], ['draft_file'], ['draft:write']),
        Registry([manifest('render', ['render'], ['draft_file'], ['draft:write'])]))
    b = spec.selected_tools[0]
    p = ToolPolicy(tenant_id=spec.tenant_id, tool_id=b.tool_id, version=b.version,
                   manifest_digest=b.digest, scopes=frozenset(b.granted_scopes),
                   effect_mode='draft_file', input_schema={'type':'object'},
                   output_schema={'type':'object'})
    recursive=[]
    recursive.append(recursive)
    gateway=VerifiedToolGateway(OversizedOutputPort(recursive), EffectLedger(),policies={'render':p})
    with pytest.raises(RuntimeDenied, match='INVALID_TOOL_OUTPUT'):
        await gateway.execute(spec,b,args={},run_id='r',step=1)


@pytest.mark.asyncio
async def test_valid_tool_output_passes_json_validation_and_returns_result():
    spec = build(task('render', ['render'], ['read'], ['read']),
                 Registry([manifest('render', ['render'], ['read'], ['read'])]))
    binding = spec.selected_tools[0]
    policy = ToolPolicy(
        tenant_id=spec.tenant_id, tool_id=binding.tool_id,
        version=binding.version, manifest_digest=binding.digest,
        scopes=frozenset(binding.granted_scopes), effect_mode='read',
        input_schema={'type': 'object'},
        output_schema={'type': 'object', 'required': ['text'],
                       'properties': {'text': {'type': 'string'}}},
    )
    port = OversizedOutputPort('verified')
    gateway = VerifiedToolGateway(port, EffectLedger(), policies={'render': policy})
    result, effect_ref = await gateway.execute(spec, binding, args={},
                                               run_id='normal-result', step=1)
    assert result == {'text': 'verified'}
    assert effect_ref.startswith('sha256:')
    assert port.calls == 1
