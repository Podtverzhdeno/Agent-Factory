"""Return saved terminal evidence after restart without repeating external effects."""

import pytest
from agent_runtime import (
    Decision,
    EffectLedger,
    Runtime,
    SqliteRunStore,
    ToolPolicy,
    VerifiedToolGateway,
)
from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task


@pytest.mark.asyncio
async def test_completed_run_retrieved_without_model_or_duplicate_effect(tmp_path):
    spec = build(task('draft',['draft'],['draft_file'],['draft:write']),
                 Registry([manifest('render',['draft'],['draft_file'],['draft:write'])]))
    b = spec.selected_tools[0]
    tools = FakeTools()
    policy = ToolPolicy(tenant_id='buyer',tool_id='render',version=b.version,
                        manifest_digest=b.digest,scopes=frozenset(b.granted_scopes),
                        effect_mode='draft_file',input_schema={'type':'object'},
                        output_schema={'type':'object'})
    def launch(decisions):
        return Runtime(ScriptedModel(decisions),VerifiedToolGateway(tools,EffectLedger(),
            policies={'render':policy}),approved_spec_digests=frozenset({spec.artifact_digest}),
            run_store=SqliteRunStore(tmp_path/'runs.db'))
    first=await launch([Decision(kind='tool',tool_id='render',args={'id':1}),
                        Decision(kind='final',text='Stored')]).run(
        spec,tenant_id='buyer',run_id='r',thread_id='t',request='create draft',trace_id='tr')
    assert first.status=='COMPLETED' and len(tools.called)==1
    second=await launch([]).run(spec,tenant_id='buyer',run_id='r',thread_id='t',
                               request='create draft',trace_id='different-trace')
    assert second==first and len(tools.called)==1
    with pytest.raises(Exception,match='RUN_IDEMPOTENCY_CONFLICT'):
        await launch([]).run(spec,tenant_id='buyer',run_id='r',thread_id='t',
                             request='changed input',trace_id='tr')
    assert SqliteRunStore(tmp_path/'runs.db').load('another','r') is None
