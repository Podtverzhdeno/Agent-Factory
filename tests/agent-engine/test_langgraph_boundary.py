"""Contract-level tenant/version checkpoint isolation without fake LangGraph compliance claims."""

import pytest
from agent_builder import digest
from agent_runtime import (
    Decision,
    EffectLedger,
    Runtime,
    RuntimeDenied,
    ToolPolicy,
    VerifiedToolGateway,
)
from agent_runtime.langgraph_adapter import invoke_graph
from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task


@pytest.mark.asyncio
async def test_checkpoint_namespace_is_tenant_agent_version_bound():
    spec = build(task('read',['read'],['read'],['read']),
                 Registry([manifest('read',['read'],['read'],['read'])]))
    b = spec.selected_tools[0]
    gateway = VerifiedToolGateway(FakeTools(),EffectLedger(),policies={'read':ToolPolicy(
        tenant_id='buyer',tool_id='read',version=b.version,manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes),effect_mode='read',
        input_schema={'type':'object'},output_schema={'type':'object'})})
    runtime = Runtime(ScriptedModel([Decision(kind='final',text='ok')]),gateway,
        approved_spec_digests=frozenset({spec.artifact_digest}))
    class FakeCompiledGraph:
        async def ainvoke(self,state,config):
            self.state,self.config=state,config
            return {'result':{'status':'COMPLETED'}}
    graph=FakeCompiledGraph()
    result=await invoke_graph(graph,runtime,spec,tenant_id='buyer',thread_id='client-thread',
        run_id='r',request='request',trace_id='tr')
    assert result['status']=='COMPLETED'
    assert graph.config['configurable']['thread_id']==digest({
        'tenant':'buyer','agent':spec.agent_id,
        'version':spec.agent_spec_version,'thread':'client-thread'})
    assert graph.config['configurable']['thread_id'] != 'client-thread'
    with pytest.raises(RuntimeDenied,match='SPEC_OR_TENANT_DENIED'):
        await invoke_graph(graph,runtime,spec,tenant_id='seller',thread_id='client-thread',
                           run_id='r',request='request',trace_id='tr')

@pytest.mark.asyncio
async def test_fresh_graph_turn_resets_old_terminal_state_and_preserves_thread_context():
    spec=build(task('read2',['read'],['read'],['read']),
        Registry([manifest('read',['read'],['read'],['read'])]))
    b=spec.selected_tools[0]
    runtime=Runtime(ScriptedModel([Decision(kind='final',text='ok')]),
        VerifiedToolGateway(FakeTools(),EffectLedger(),policies={'read':ToolPolicy(
            tenant_id='buyer',tool_id='read',version=b.version,manifest_digest=b.digest,
            scopes=frozenset(b.granted_scopes),input_schema={'type':'object'},
            output_schema={'type':'object'},effect_mode='read')}),
        approved_spec_digests=frozenset([spec.artifact_digest]))
    runtime.memory.append('buyer',spec.agent_id,'thread',{'role':'assistant','content':'previous'})
    class Graph:
        async def ainvoke(self,state,config):
            self.received=state
            return {'result':{'status':'COMPLETED'}}
    graph=Graph()
    await invoke_graph(graph,runtime,spec,tenant_id='buyer',thread_id='thread',
                       run_id='r',request='new',trace_id='tr')
    assert graph.received['history']==[{'role':'assistant','content':'previous'},
                                      {'role':'user','content':'new'}]
    assert graph.received['steps']==0 and graph.received['cost_usd']==0
    assert graph.received['pending_tool']=='' and graph.received['terminal_error'] is None
    assert graph.received['result'] == {}
