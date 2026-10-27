"""Two independently authorized organizations using real official A2A SDK transport.

This is a wire-level smoke and tenant-isolation test. It does not claim a
multi-turn negotiated RFQ or a verified commercial-offer business outcome.
"""
import httpx
import pytest

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


def server(tenant: str, principal: str, answer: str):
    from a2a.types import (
        AgentCapabilities,
        AgentCard,
        AgentInterface,
        AgentSkill,
    )

    snap = task(f'{tenant}-catalog', ['lookup'], ['read'], ['catalog:read'],
                tenant=tenant)
    spec = build(snap, Registry([
        manifest(f'{tenant}.lookup', ['lookup'], ['read'], ['catalog:read'],
                 tenant=tenant)]))
    binding = spec.selected_tools[0]
    tools = FakeTools()
    gateway = VerifiedToolGateway(tools, EffectLedger(), policies={
        binding.tool_id: ToolPolicy(
            tenant_id=tenant, tool_id=binding.tool_id,
            version=binding.version, manifest_digest=binding.digest,
            scopes=frozenset(binding.granted_scopes),
            effect_mode='read', input_schema={'type': 'object'},
            output_schema={'type': 'object'}),
    })
    runtime = Runtime(
        ScriptedModel([Decision(kind='final', text=answer)]), gateway,
        approved_spec_digests=frozenset({spec.artifact_digest}))
    boundary = A2ABoundary(
        released_spec_digests=frozenset({spec.artifact_digest}),
        authorize=lambda auth_principal, auth_tenant: (
            auth_tenant == tenant and auth_principal == principal))
    card = AgentCard(
        name=f'{tenant} A2A candidate', description='Synthetic isolated test',
        version='0.1.0', default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[
            AgentInterface(protocol_binding='JSONRPC', url='http://localhost/')],
        skills=[AgentSkill(
            id='lookup', name='Catalog lookup',
            description='Read authorized synthetic catalog',
            tags=['synthetic'], examples=['Read catalog'])])
    app = create_official_a2a_app(
        spec=spec, runtime=runtime, boundary=boundary, agent_card=card,
        authenticate=lambda token: A2AIdentity(tenant, principal)
        if token == f'{tenant}-token' else None,
        principal_scope=principal)
    return app, spec, runtime, tools


@pytest.mark.asyncio
async def test_two_tenants_real_a2a_sdk_clients_are_isolated():
    pytest.importorskip('a2a')
    from a2a.client import A2ACardResolver, ClientConfig, create_client
    from a2a.helpers import new_text_message
    from a2a.types import Role, SendMessageRequest

    buyer_app, buyer_spec, buyer_runtime, buyer_tools = server(
        'buyer', 'buyer-principal', 'Buyer RFQ acknowledged')
    supplier_app, supplier_spec, supplier_runtime, supplier_tools = server(
        'supplier', 'supplier-principal', 'Supplier quotation draft prepared')

    assert buyer_spec.verify_digest() and supplier_spec.verify_digest()
    assert buyer_spec.tenant_id != supplier_spec.tenant_id
    assert set(b.tool_id for b in buyer_spec.selected_tools) == {'buyer.lookup'}
    assert set(b.tool_id for b in supplier_spec.selected_tools) == {'supplier.lookup'}

    for app, tenant, other_tenant, runtime, tools in [
        (buyer_app, 'buyer', 'supplier', buyer_runtime, buyer_tools),
        (supplier_app, 'supplier', 'buyer', supplier_runtime, supplier_tools),
    ]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url='http://localhost',
            headers={'Authorization': f'Bearer {tenant}-token'},
        ) as http:
            card = await A2ACardResolver(
                httpx_client=http, base_url='http://localhost').get_agent_card()
            assert card.name == f'{tenant} A2A candidate'
            client = await create_client(
                agent=card, client_config=ClientConfig(
                    streaming=False, httpx_client=http))
            try:
                replies = []
                async for event in client.send_message(SendMessageRequest(
                    message=new_text_message('Read approved catalog',
                                             role=Role.ROLE_USER))):
                    replies.append(event)
                assert replies
            finally:
                await client.close()
            # A token minted for the other organization cannot read even
            # the agent card, much less messages or task state.
            assert (await http.get('/.well-known/agent-card.json', headers={
                'Authorization': f'Bearer {other_tenant}-token'})).status_code == 401
            assert not tools.called
            assert runtime.memory.get(other_tenant, 'unrelated-agent', 'other-thread') == []
