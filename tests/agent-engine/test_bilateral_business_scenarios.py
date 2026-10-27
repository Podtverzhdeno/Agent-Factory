"""Bilateral business fixtures: contract-level only, NOT official A2A wire E2E.

Scenarios are traced to AF-REQ-031/038 and AF-REQ-004/005/012/037.
These fixtures prove isolation of independent Builder/Runtime instances;
a separate SDK test must prove multi-turn A2A protocol conformance.
"""
import pytest
from agent_builder import BuildError
from agent_runtime import A2ABoundary, Decision, RuntimeDenied
from test_engine import Registry, build, invoke, manifest, task


def bilateral_specs():
    registry = Registry([
        manifest('buyer.catalog', ['catalog.read'], ['read'], ['catalog:read'],
                 tenant='buyer'),
        manifest('supplier.stock', ['inventory.read'], ['read'], ['stock:read'],
                 tenant='supplier'),
        manifest('supplier.quote', ['quotation.draft'], ['draft_file'], ['quote:draft'],
                 tenant='supplier'),
        manifest('payment.execute', ['payment'], ['payment'], ['payments:write'],
                 tenant='buyer'),
    ])
    buyer = build(task('purchase-rfq', ['catalog.read'], ['read'],
                       ['catalog:read'], tenant='buyer'), registry)
    supplier = build(task('supplier-quote', ['inventory.read', 'quotation.draft'],
                          ['read', 'draft_file'], ['stock:read', 'quote:draft'],
                          tenant='supplier'), registry)
    return registry, buyer, supplier


@pytest.mark.asyncio
async def test_bilateral_scenario_two_independent_tenant_pinned_agents():
    _, buyer, supplier = bilateral_specs()
    assert buyer.tenant_id == 'buyer' and supplier.tenant_id == 'supplier'
    assert buyer.agent_id != supplier.agent_id
    assert buyer.artifact_digest != supplier.artifact_digest
    assert buyer.verify_digest() and supplier.verify_digest()
    assert {t.tool_id for t in buyer.selected_tools} == {'buyer.catalog'}
    assert {t.tool_id for t in supplier.selected_tools} == {
        'supplier.stock', 'supplier.quote'}
    assert 'payment.execute' not in {
        t.tool_id for s in (buyer, supplier) for t in s.selected_tools}

    # Deterministic port-level simulation. No A2A SDK or partner transport here.
    buyer_runtime, buyer_tools = invoke(buyer, [
        Decision(kind='tool', tool_id='buyer.catalog', args={'sku': 'BOLT-1'}),
        Decision(kind='final', text='Synthetic buyer RFQ prepared'),
    ])
    supplier_runtime, supplier_tools = invoke(supplier, [
        Decision(kind='tool', tool_id='supplier.stock', args={'sku': 'BOLT-1'}),
        Decision(kind='tool', tool_id='supplier.quote', args={'qty': 2}),
        Decision(kind='final', text='Synthetic supplier draft prepared'),
    ])
    first = await buyer_runtime.run(
        buyer, tenant_id='buyer', run_id='buyer-rfq-1',
        thread_id='buyer-thread-1', request='Need two bolts',
        trace_id='buyer-trace')
    second = await supplier_runtime.run(
        supplier, tenant_id='supplier', run_id='supplier-quote-1',
        thread_id='supplier-thread-1', request='Draft a quote for two bolts',
        trace_id='supplier-trace')
    assert first.status == 'COMPLETED'
    assert second.status == 'COMPLETED'
    assert len(buyer_tools.called) == 1
    assert len(supplier_tools.called) == 2
    assert {item[0] for item in buyer_tools.called} == {'buyer'}
    assert {item[0] for item in supplier_tools.called} == {'supplier'}
    assert buyer_runtime.memory.get('supplier', buyer.agent_id, 'buyer-thread-1') == []
    assert supplier_runtime.memory.get('buyer', supplier.agent_id, 'supplier-thread-1') == []


@pytest.mark.asyncio
async def test_bilateral_scenario_cross_tenant_runtime_and_a2a_denied():
    _, buyer, supplier = bilateral_specs()
    supplier_runtime, tools = invoke(supplier, [
        Decision(kind='tool', tool_id='supplier.stock', args={})])
    with pytest.raises(RuntimeDenied, match='TENANT_DENIED'):
        await supplier_runtime.run(
            supplier, tenant_id='buyer', run_id='wrong-tenant',
            thread_id='buyer-thread', request='Read seller stock', trace_id='deny')
    assert tools.called == []
    boundary = A2ABoundary(
        released_spec_digests=frozenset({supplier.artifact_digest}),
        authorize=lambda principal, tenant: principal == 'buyer' and tenant == 'buyer')
    with pytest.raises(RuntimeDenied, match='A2A_TENANT_DENIED'):
        boundary.authorize_request(tenant_id='buyer', principal='buyer', spec=supplier)


def test_bilateral_scenario_missing_partner_connector_blocks_only_that_build():
    registry = Registry([
        manifest('buyer.catalog', ['catalog.read'], ['read'], ['catalog:read'],
                 tenant='buyer')])
    buyer = build(task('purchase-rfq', ['catalog.read'], ['read'],
                       ['catalog:read'], tenant='buyer'), registry)
    with pytest.raises(BuildError, match='CAPABILITY_DENIED'):
        build(task('supplier-quote', ['inventory.read'], ['read'],
                   ['stock:read'], tenant='supplier'), registry)
    assert buyer.verify_digest()  # The other organization's build is untouched.


def test_bilateral_scenario_cannot_repurpose_draft_authority_as_payment():
    _, buyer, _ = bilateral_specs()
    with pytest.raises(BuildError, match='EFFECT_POLICY_DENIED'):
        build(task('unsafe-order', ['payment'], ['payment'],
                   ['payments:write'], tenant='buyer'),
              Registry([manifest('payment.execute', ['payment'], ['payment'],
                                 ['payments:write'], tenant='buyer')]))
    assert buyer.verify_digest()
