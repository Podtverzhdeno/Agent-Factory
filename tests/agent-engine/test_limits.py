"""Input bounds, memory retention and expiry regression tests."""
import pytest

from agent_runtime import (
    Decision,
    EffectLedger,
    Runtime,
    RuntimeDenied,
    SqliteMemory,
    ThreadMemory,
    ToolPolicy,
    VerifiedToolGateway,
)
from test_engine import build, FakeTools, manifest, Registry, ScriptedModel, task


def make_runtime():
    spec=build(task('read',['read'],['read'],['read']),
        Registry([manifest('r',['read'],['read'],['read'])]))
    b=spec.selected_tools[0]
    gateway=VerifiedToolGateway(FakeTools(),EffectLedger(),policies={'r':ToolPolicy(
        tenant_id='buyer',tool_id=b.tool_id,version=b.version,manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes),input_schema={'type':'object'},
        output_schema={'type':'object'},effect_mode='read')})
    return spec,Runtime(ScriptedModel([Decision(kind='final',text='ok')]),gateway,
        approved_spec_digests=frozenset([spec.artifact_digest]))

@pytest.mark.asyncio
async def test_oversized_or_invalid_run_input_rejected():
    spec,runtime=make_runtime()
    with pytest.raises(RuntimeDenied,match='INVALID_RUN_INPUT'):
        await runtime.run(spec,tenant_id='buyer',run_id='r',thread_id='t',
            request='x'*20001,trace_id='tr')
    with pytest.raises(RuntimeDenied,match='INVALID_RUN_INPUT'):
        await runtime.run(spec,tenant_id='buyer',run_id='r',thread_id='',
            request='hello',trace_id='tr')

def test_bounded_thread_memory_and_durable_expiry_cleanup(tmp_path):
    memory=ThreadMemory()
    for n in range(110):
        memory.append('buyer','agent','thread',{'n':n})
    history=memory.get('buyer','agent','thread')
    assert len(history)==50 and history[0]['n']==60
    with pytest.raises(RuntimeDenied,match='MEMORY_TOO_LARGE'):
        memory.append('buyer','agent','thread',{'text':'x'*16001})
    clock=[10]
    durable=SqliteMemory(tmp_path/'m.db',clock=lambda:clock[0])
    durable.put('buyer','agent','temp','ttl',ttl_seconds=2)
    clock[0]=13
    assert durable.purge_expired()==1
    assert durable.get_long('buyer','agent','temp') is None

@pytest.mark.asyncio
async def test_slow_model_blocked_without_tool_effect():
    import asyncio
    spec, _ = make_runtime()
    class HangingModel:
        async def decide(self, **kwargs):
            await asyncio.sleep(0.3)
            return Decision(kind='final', text='late')
    b=spec.selected_tools[0]
    tools=FakeTools()
    runtime=Runtime(HangingModel(),VerifiedToolGateway(tools,EffectLedger(),policies={'r':ToolPolicy(
        tenant_id='buyer',tool_id=b.tool_id,version=b.version,manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes),input_schema={'type':'object'},
        output_schema={'type':'object'},effect_mode='read')}),
        approved_spec_digests=frozenset({spec.artifact_digest}),model_timeout_seconds=0.01)
    result=await runtime.run(spec,tenant_id='buyer',run_id='r',thread_id='t',
                             request='Hello',trace_id='trace')
    assert result.status=='BLOCKED' and result.error_code=='MODEL_TIMEOUT'
    assert not tools.called

@pytest.mark.parametrize('bad_cost', [float('nan'),float('inf'),float('-inf')])
def test_decision_rejects_nonfinite_cost(bad_cost):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Decision(kind='final',text='complete',estimated_usd=bad_cost)
