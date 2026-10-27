"""AF-REQ-007/012/016/029: disk crash, tenant and tool authority tests."""
import asyncio
import pytest
from agent_runtime import (Decision, EffectLedger, Runtime, RuntimeDenied,
                           SqliteEffectLedger, SqliteMemory, ToolPolicy, VerifiedToolGateway)
from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task

def spec():
    return build(task('draft', ['draft'], ['draft_file'], ['draft:write']),
                 Registry([manifest('render', ['draft'], ['draft_file'], ['draft:write'])]))

def policy(binding, **overrides):
    data = dict(tenant_id='buyer', tool_id=binding.tool_id, version=binding.version,
                manifest_digest=binding.digest, scopes=frozenset(binding.granted_scopes),
                effect_mode=binding.side_effects[0], input_schema={'type':'object'},
                output_schema={'type':'object'})
    data.update(overrides)
    return ToolPolicy(**data)

@pytest.mark.asyncio
async def test_durable_effect_replay_denied_after_restart(tmp_path):
    s = spec()
    db = tmp_path / 'effects.db'
    tools = FakeTools(crash_after_commit=True)
    def runtime(ledger):
        return Runtime(ScriptedModel([Decision(kind='tool', tool_id='render', args={'id':1})]),
            VerifiedToolGateway(tools, ledger,
                policies={'render':policy(s.selected_tools[0])}),
            approved_spec_digests=frozenset([s.artifact_digest]))
    a = await runtime(SqliteEffectLedger(db)).run(s, tenant_id='buyer', run_id='r',
        thread_id='t', request='q', trace_id='tr')
    assert a.error_code == 'EXECUTION_UNCERTAIN'
    b = await runtime(SqliteEffectLedger(db)).run(s, tenant_id='buyer', run_id='r',
        thread_id='t', request='q', trace_id='tr')
    assert b.error_code == 'EFFECT_REPLAY_REQUIRES_RECONCILIATION'
    assert len(tools.called) == 1

@pytest.mark.asyncio
async def test_atomic_effect_reservation_across_connections(tmp_path):
    p = tmp_path / 'effects.db'
    ledgers = [SqliteEffectLedger(p), SqliteEffectLedger(p)]
    async def reserve(ledger):
        try:
            await ledger.reserve('same-effect')
            return 'RESERVED'
        except RuntimeDenied as exc:
            return exc.code
    assert sorted(await asyncio.gather(*(reserve(x) for x in ledgers))) == [
        'EFFECT_REPLAY_REQUIRES_RECONCILIATION', 'RESERVED']

@pytest.mark.asyncio
async def test_pin_scope_schema_and_output_validation_before_effect():
    s = spec()
    b = s.selected_tools[0]
    tools, ledger = FakeTools(), EffectLedger()
    good = policy(b, input_schema={'type':'object', 'properties':{'id':{'type':'integer'}},
                                   'required':['id'], 'additionalProperties':False})
    gateway = VerifiedToolGateway(tools, ledger, policies={'render':good})
    with pytest.raises(RuntimeDenied, match='INVALID_TOOL_INPUT'):
        await gateway.execute(s, b, args={'id':'bad'}, run_id='r', step=1)
    assert not tools.called
    invalid = good.model_copy(update={'manifest_digest':'sha256:wrong'})
    with pytest.raises(RuntimeDenied, match='TOOL_PIN_OR_SCOPE_DENIED'):
        await VerifiedToolGateway(tools, ledger, policies={'render':invalid}).execute(
            s, b, args={'id':1}, run_id='r', step=1)
    result, key = await gateway.execute(s, b, args={'id':1}, run_id='r', step=1)
    assert result['ok'] is True and ledger.status(key) == 'CONFIRMED'
    assert len(tools.called) == 1

@pytest.mark.asyncio
async def test_invalid_response_leaves_effect_uncertain():
    s = spec()
    b = s.selected_tools[0]
    tools, ledger = FakeTools(), EffectLedger()
    gateway = VerifiedToolGateway(tools, ledger, policies={'render':policy(
        b, output_schema={'type':'object', 'required':['nonexistent']})})
    with pytest.raises(RuntimeDenied, match='INVALID_TOOL_OUTPUT'):
        await gateway.execute(s, b, args={'id':1}, run_id='r', step=1)
    key = tools.called[0][3]
    assert ledger.status(key) == 'UNCERTAIN'
    with pytest.raises(RuntimeDenied, match='EFFECT_REPLAY_REQUIRES_RECONCILIATION'):
        await gateway.execute(s, b, args={'id':1}, run_id='r', step=1)
    assert len(tools.called) == 1

def test_untrusted_schema_reference_denied():
    s = spec()
    with pytest.raises(RuntimeDenied, match='UNTRUSTED_SCHEMA_REFERENCE'):
        VerifiedToolGateway(FakeTools(), EffectLedger(), policies={'render': policy(
            s.selected_tools[0], input_schema={'$ref':'https://untrusted.example/s'})})

def test_tenant_memory_after_restart_and_expiry(tmp_path):
    now = [10.0]
    path = tmp_path / 'memory.db'
    m = SqliteMemory(path, clock=lambda:now[0])
    m.append('buyer', 'agent-a', 't', {'content':'test'})
    m.put('buyer', 'agent-a', 'k', 'approved', ttl_seconds=5)
    restart = SqliteMemory(path, clock=lambda:now[0])
    assert restart.get('buyer', 'agent-a', 't') == [{'content':'test'}]
    assert restart.get('seller', 'agent-a', 't') == []
    assert restart.get_long('buyer', 'agent-a', 'k') == 'approved'
    assert restart.get_long('seller', 'agent-a', 'k') is None
    now[0] = 15
    assert restart.get_long('buyer', 'agent-a', 'k') is None

@pytest.mark.asyncio
async def test_runtime_denies_unverified_gateway():
    from agent_runtime import ToolGateway
    s = spec()
    from test_engine import FakeTools
    runtime = Runtime(ScriptedModel([Decision(kind='final',text='ok')]),
                      ToolGateway(FakeTools(), EffectLedger()),
                      approved_spec_digests=frozenset([s.artifact_digest]))
    with pytest.raises(RuntimeDenied, match='UNVERIFIED_TOOL_GATEWAY'):
        await runtime.run(s, tenant_id='buyer', run_id='run', thread_id='t',
                          request='test', trace_id='tr')

@pytest.mark.asyncio
async def test_tool_timeout_keeps_effect_uncertain():
    s = spec()
    b = s.selected_tools[0]
    class HangingTools:
        def __init__(self):
            self.calls = 0
        async def call(self, **kwargs):
            self.calls += 1
            await asyncio.sleep(0.2)
            return {'ok':True}
    tools = HangingTools()
    gateway = VerifiedToolGateway(tools, EffectLedger(),
        policies={'render':policy(b)}, timeout_seconds=0.01)
    with pytest.raises(RuntimeDenied, match='TOOL_TIMEOUT_UNCERTAIN'):
        await gateway.execute(s,b,args={},run_id='r',step=1)
    with pytest.raises(RuntimeDenied, match='EFFECT_REPLAY_REQUIRES_RECONCILIATION'):
        await gateway.execute(s,b,args={},run_id='r',step=1)
    assert tools.calls == 1
