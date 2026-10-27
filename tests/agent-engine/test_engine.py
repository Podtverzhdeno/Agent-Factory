"""AF-REQ-005/006/007/012/013/016/029 negative and two-task component tests."""
import pytest

from agent_builder import (
    BuildCommand,
    Builder,
    BuildError,
    Limits,
    TaskSnapshot,
    ToolManifest,
)
from agent_runtime import (
    A2ABoundary,
    Decision,
    EffectLedger,
    LongTermMemory,
    Runtime,
    RuntimeDenied,
    ThreadMemory,
    ToolGateway,
    ToolPolicy,
    VerifiedToolGateway,
)


SHA = 'sha256:' + 'a' * 64

class Registry:
    def __init__(self, manifests):
        self.manifests = manifests
    def eligible_manifests(self, tenant_id):
        return list(self.manifests)

def manifest(tool, caps, effects, scopes, *, tenant='buyer', approved=True):
    return ToolManifest(tool_id=tool, version='1.0.0', manifest_digest=SHA,
        capabilities=frozenset(caps), side_effects=frozenset(effects),
        required_scopes=frozenset(scopes), tenant_availability=frozenset([tenant]),
        input_schema_ref='artifact://schemas/in-v1', output_schema_ref='artifact://schemas/out-v1',
        risk_level='low', approved=approved, transport='LOCAL')

def task(name, caps, effects, scopes, tenant='buyer'):
    return TaskSnapshot(tenant_id=tenant, task_id=name, task_snapshot_id='snap-' + name,
        status='READY', objective='Complete approved synthetic workflow for ' + name,
        required_capabilities=tuple(caps), allowed_effects=frozenset(effects),
        authorized_scopes=frozenset(scopes), acceptance_policy_ref='artifact://policies/acceptance-v1',
        snapshot_digest=SHA, limits=Limits(max_steps=5, max_usd_per_run=0.5))

def build(t, registry):
    return Builder(registry, frozenset(['mock-model'])).assemble(t,
        BuildCommand(build_id='build-1', tenant_id=t.tenant_id,
            task_snapshot_id=t.task_snapshot_id, idempotency_key='idem-1',
            capability_registry_revision='r1', model_route='mock-model',
            evaluation_policy_ref=t.acceptance_policy_ref))

class ScriptedModel:
    def __init__(self, decisions):
        self.decisions = list(decisions)
    async def decide(self, **kwargs):
        return self.decisions.pop(0)

class FakeTools:
    def __init__(self, crash_after_commit=False):
        self.called = []
        self.crash_after_commit = crash_after_commit
    async def call(self, *, tenant_id, tool_id, args, idempotency_key):
        self.called.append((tenant_id, tool_id, args, idempotency_key))
        if self.crash_after_commit:
            raise OSError('synthetic crash after remote commit')
        return {'ok': True, 'ref': 'artifact://synthetic/output'}

def invoke(spec, decisions, *, tools=None, ledger=None, memory=None):
    tools = tools or FakeTools()
    policies = {b.tool_id: ToolPolicy(tenant_id=spec.tenant_id, tool_id=b.tool_id,
        version=b.version, manifest_digest=b.digest, scopes=frozenset(b.granted_scopes),
        effect_mode=b.side_effects[0], input_schema={'type': 'object'},
        output_schema={'type': 'object'}) for b in spec.selected_tools}
    runtime = Runtime(ScriptedModel(decisions),
        VerifiedToolGateway(tools, ledger or EffectLedger(), policies=policies),
        memory, approved_spec_digests=frozenset([spec.artifact_digest]))
    return runtime, tools

@pytest.mark.asyncio
async def test_two_distinct_business_tasks_use_same_builder_and_runtime():
    reg = Registry([manifest('catalog.lookup', ['catalog_lookup'], ['read'], ['catalog:read']),
                    manifest('rfq.render', ['draft_quote'], ['draft_file'], ['draft:write']),
                    manifest('supplier.check', ['supplier_check'], ['read'], ['supplier:read']),
                    manifest('unused.pay', ['payment'], ['payment'], ['payments:execute'])])
    rfq = build(task('rfq', ['catalog_lookup', 'draft_quote'], ['read', 'draft_file'],
                     ['catalog:read', 'draft:write']), reg)
    supplier = build(task('supplier', ['supplier_check'], ['read'], ['supplier:read']), reg)
    assert rfq.agent_id != supplier.agent_id and rfq.artifact_digest != supplier.artifact_digest
    assert {x.tool_id for x in rfq.selected_tools} == {'catalog.lookup', 'rfq.render'}
    assert [x.tool_id for x in supplier.selected_tools] == ['supplier.check']
    assert rfq.verify_digest() and supplier.verify_digest()
    for spec, actions in [(rfq, ['catalog.lookup', 'rfq.render']), (supplier, ['supplier.check'])]:
        decisions = [Decision(kind='tool', tool_id=tid, args={'id': 'synthetic'}) for tid in actions]
        decisions.append(Decision(kind='final', text='Draft prepared from returned evidence'))
        runtime, tools = invoke(spec, decisions)
        result = await runtime.run(spec, tenant_id='buyer', run_id='run-' + spec.agent_id,
            thread_id='thread', request='prepare document', trace_id='tr1')
        assert result.status == 'COMPLETED'
        assert len(tools.called) == len(actions)
        assert len(result.tool_effect_refs) == len(actions)

def test_minimal_set_cover_is_deterministic():
    reg = Registry([manifest('two-in-one', ['a', 'b'], ['read'], ['read']),
                    manifest('a', ['a'], ['read'], ['read']),
                    manifest('b', ['b'], ['read'], ['read'])])
    t = task('combine', ['a', 'b'], ['read'], ['read'])
    a, b = build(t, reg), build(t, reg)
    assert [x.tool_id for x in a.selected_tools] == ['two-in-one']
    assert a == b

def test_forbidden_tools_or_missing_grant_fail_closed():
    reg = Registry([manifest('pay', ['payment'], ['payment'], ['payments:execute'])])
    with pytest.raises(BuildError, match='CAPABILITY_DENIED'):
        build(task('payments', ['payment'], ['read'], []), reg)
    with pytest.raises(BuildError, match='EFFECT_POLICY_DENIED'):
        build(task('payments', ['payment'], ['payment'], []), reg)
    reg = Registry([manifest('denied', ['catalog_lookup'], ['read'], [], approved=False)])
    with pytest.raises(BuildError, match='CAPABILITY_DENIED'):
        build(task('denied', ['catalog_lookup'], ['read'], []), reg)

@pytest.mark.asyncio
async def test_forbidden_tool_and_tenant_rejected():
    s = build(task('read', ['read'], ['read'], ['read']),
              Registry([manifest('read.tool', ['read'], ['read'], ['read'])]))
    runtime, tools = invoke(s, [Decision(kind='tool', tool_id='evil.pay')])
    with pytest.raises(RuntimeDenied, match='TENANT_DENIED'):
        await runtime.run(s, tenant_id='another', run_id='r', thread_id='t', request='r', trace_id='tr')
    result = await runtime.run(s, tenant_id='buyer', run_id='r', thread_id='t', request='r', trace_id='tr')
    assert result.status == 'BLOCKED' and result.error_code == 'TOOL_DENIED'
    assert tools.called == []

@pytest.mark.asyncio
async def test_external_effect_is_never_replayed_after_unknown_result():
    s = build(task('draft', ['draft'], ['draft_file'], ['draft:write']),
              Registry([manifest('render', ['draft'], ['draft_file'], ['draft:write'])]))
    ledger = EffectLedger()
    tools = FakeTools(crash_after_commit=True)
    runtime, _ = invoke(s, [Decision(kind='tool', tool_id='render', args={'x': 1})],
                        ledger=ledger, tools=tools)
    first = await runtime.run(s, tenant_id='buyer', run_id='r', thread_id='t', request='q', trace_id='tr')
    assert first.status == 'BLOCKED' and first.error_code == 'EXECUTION_UNCERTAIN'
    assert len(tools.called) == 1
    restarted, _ = invoke(s, [Decision(kind='tool', tool_id='render', args={'x': 1})],
                          ledger=ledger, tools=tools)
    second = await restarted.run(s, tenant_id='buyer', run_id='r', thread_id='t', request='q', trace_id='tr')
    assert second.error_code == 'EFFECT_REPLAY_REQUIRES_RECONCILIATION'
    assert len(tools.called) == 1
    same = await runtime.run(s, tenant_id='buyer', run_id='r', thread_id='t', request='q', trace_id='tr')
    assert same == first
    with pytest.raises(RuntimeDenied, match='RUN_IDEMPOTENCY_CONFLICT'):
        await runtime.run(s, tenant_id='buyer', run_id='r', thread_id='t', request='changed', trace_id='tr')

@pytest.mark.asyncio
async def test_budget_steps_and_spec_tamper():
    s = build(task('limits', ['read'], ['read'], ['read']),
              Registry([manifest('read.tool', ['read'], ['read'], ['read'])]))
    runtime, tools = invoke(s, [Decision(kind='final', text='done', estimated_usd=1.0)])
    res = await runtime.run(s, tenant_id='buyer', run_id='r', thread_id='t', request='r', trace_id='tr')
    assert res.error_code == 'BUDGET_EXCEEDED'
    tampered = s.model_copy(update={'model_route': 'unapproved'})
    with pytest.raises(RuntimeDenied, match='SPEC_TAMPERED'):
        await runtime.run(tampered, tenant_id='buyer', run_id='r2', thread_id='t', request='r', trace_id='tr')

def test_scoped_memories_and_ttl():
    clock = [100.0]
    memory = LongTermMemory(clock=lambda: clock[0])
    memory.put('buyer', 'agent-a', 'supplier', 'approved supplier', ttl_seconds=5)
    assert memory.get('buyer', 'agent-a', 'supplier') == 'approved supplier'
    assert memory.get('seller', 'agent-a', 'supplier') is None
    assert memory.get('buyer', 'agent-b', 'supplier') is None
    clock[0] = 106
    assert memory.get('buyer', 'agent-a', 'supplier') is None
    threads = ThreadMemory()
    threads.append('buyer', 'agent-a', 'thread', {'content': 'secret'})
    assert threads.get('buyer', 'agent-a', 'thread') == [{'content': 'secret'}]
    assert threads.get('seller', 'agent-a', 'thread') == []

def test_a2a_boundary_denies_unreleased_and_wrong_caller():
    s = build(task('read', ['read'], ['read'], []),
              Registry([manifest('r', ['read'], ['read'], [])]))
    a2a = A2ABoundary(released_spec_digests=frozenset(),
                      authorize=lambda principal, tenant: principal == 'approved' and tenant == 'buyer')
    with pytest.raises(RuntimeDenied, match='A2A_UNAUTHORIZED'):
        a2a.authorize_request(tenant_id='buyer', principal='anonymous', spec=s)
    with pytest.raises(RuntimeDenied, match='A2A_NOT_RELEASED'):
        a2a.authorize_request(tenant_id='buyer', principal='approved', spec=s)

@pytest.mark.parametrize('kwargs', [
    {'kind': 'tool', 'args': {}},
    {'kind': 'tool', 'tool_id': 'read', 'text': 'done'},
    {'kind': 'final', 'tool_id': 'pay', 'text': 'done'},
    {'kind': 'final', 'args': {'x':1}, 'text': 'done'}
])
def test_decision_rejects_conflicting_tool_and_final_actions(kwargs):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Decision(**kwargs)
