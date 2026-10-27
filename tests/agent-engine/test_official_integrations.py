"""SDK and PostgreSQL integration contracts: SKIP unless real dependencies are present."""

import os

from langchain_core.runnables.config import RunnableConfig

import pytest


@pytest.mark.asyncio
async def test_real_langgraph_inmemory_graph():
    pytest.importorskip('langgraph')
    from agent_runtime import (
        Decision,
        EffectLedger,
        Runtime,
        ToolPolicy,
        VerifiedToolGateway,
    )
    from agent_runtime.langgraph_adapter import build_graph, invoke_graph
    from langgraph.checkpoint.memory import InMemorySaver
    from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task
    spec = build(task('read',['read'],['read'],['read']),
                 Registry([manifest('read',['read'],['read'],['read'])]))
    b = spec.selected_tools[0]
    gateway = VerifiedToolGateway(FakeTools(), EffectLedger(), policies={'read': ToolPolicy(
        tenant_id='buyer',tool_id='read',version=b.version,manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes),effect_mode='read',
        input_schema={'type':'object'},output_schema={'type':'object'})})
    runtime = Runtime(ScriptedModel([Decision(kind='tool',tool_id='read',args={}),
                                    Decision(kind='final',text='Done')]),gateway,
                      approved_spec_digests=frozenset({spec.artifact_digest}))
    graph = build_graph(runtime, spec, InMemorySaver())
    result = await invoke_graph(graph, runtime, spec, tenant_id='buyer',
        thread_id='t', run_id='r', request='read approved catalog', trace_id='trace')
    assert result['status'] == 'COMPLETED'
    assert result['steps'] == 2
    assert len(result['tool_effect_refs']) == 1

@pytest.mark.asyncio
async def test_real_postgres_saver_initialization():
    pytest.importorskip('langgraph')
    pytest.importorskip('langgraph.checkpoint.postgres.aio')
    dsn = os.getenv('AGENT_ENGINE_TEST_PG_DSN')
    if not dsn:
        pytest.skip('AGENT_ENGINE_TEST_PG_DSN required for real PostgreSQL test')
    from typing import TypedDict
    from uuid import uuid4

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        counter: int

    def compile_graph(saver):
        graph = StateGraph(State)
        graph.add_node('increment', lambda state: {'counter':state['counter']+1})
        graph.add_edge(START,'increment')
        graph.add_edge('increment',END)
        return graph.compile(checkpointer=saver)

    config: RunnableConfig = {'configurable':{'thread_id':'af04-test-'+str(uuid4())}}
    async with AsyncPostgresSaver.from_conn_string(dsn) as first:
        await first.setup()
        graph=compile_graph(first)
        assert (await graph.ainvoke({'counter':1},config=config))['counter']==2
    async with AsyncPostgresSaver.from_conn_string(dsn) as reopened:
        graph=compile_graph(reopened)
        checkpoint=await graph.aget_state(config)
        values = checkpoint.values
        assert isinstance(values, dict)
        assert values['counter']==2
        assert (await graph.ainvoke({'counter':2},config=config))['counter']==3

@pytest.mark.asyncio
async def test_official_a2a_sdk_client_server_smoke():
    pytest.importorskip('a2a')
    import httpx
    from a2a.client import A2ACardResolver, ClientConfig, create_client
    from a2a.helpers import new_text_message
    from a2a.types import (
        AgentCapabilities,
        AgentCard,
        AgentInterface,
        AgentSkill,
        Role,
        SendMessageRequest,
    )
    from agent_runtime import (
        A2ABoundary,
        Decision,
        EffectLedger,
        Runtime,
        ToolPolicy,
        VerifiedToolGateway,
    )
    from agent_runtime.official_a2a import A2AIdentity, create_official_a2a_app
    from test_engine import FakeTools, Registry, ScriptedModel, build, manifest, task
    spec = build(task('read',['read'],['read'],['read']),
                 Registry([manifest('read',['read'],['read'],['read'])]))
    b = spec.selected_tools[0]
    gateway = VerifiedToolGateway(FakeTools(), EffectLedger(), policies={'read':ToolPolicy(
        tenant_id='buyer',tool_id='read',version=b.version,manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes),effect_mode='read',
        input_schema={'type':'object'},output_schema={'type':'object'})})
    runtime = Runtime(ScriptedModel([Decision(kind='final',text='Synthetic verified data')]),
                      gateway, approved_spec_digests=frozenset({spec.artifact_digest}))
    boundary = A2ABoundary(released_spec_digests=frozenset({spec.artifact_digest}),
                           authorize=lambda principal, tenant: principal == 'trusted' and tenant == 'buyer')
    card = AgentCard(name='Synthetic test agent',description='Sandbox-only agent',
                     version='0.1.0',default_input_modes=['text/plain'],
                     default_output_modes=['text/plain'],capabilities=AgentCapabilities(streaming=False),
                     supported_interfaces=[AgentInterface(protocol_binding='JSONRPC',url='http://localhost/')],
                     skills=[AgentSkill(id='read',name='Read',description='Read permitted catalog',
                                        tags=['sandbox'],examples=['Read catalog'])])
    app = create_official_a2a_app(spec=spec,runtime=runtime,boundary=boundary,agent_card=card,
               authenticate=lambda token: A2AIdentity('buyer','trusted') if token == 'good' else None,
               principal_scope='trusted')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost',
                                 headers={'Authorization':'Bearer good'}) as client_http:
        resolver = A2ACardResolver(httpx_client=client_http,base_url='http://localhost')
        resolved = await resolver.get_agent_card()
        assert resolved.name == 'Synthetic test agent'
        client = await create_client(agent=resolved,client_config=ClientConfig(
            streaming=False,httpx_client=client_http))
        try:
            replies = []
            async for event in client.send_message(SendMessageRequest(
                message=new_text_message('Read catalog',role=Role.ROLE_USER))):
                replies.append(event)
            assert replies
        finally:
            await client.close()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://localhost') as anonymous:
        assert (await anonymous.get('/.well-known/agent-card.json')).status_code == 401
