"""Builder command idempotency and tenant isolation (AF-REQ-005/006/029)."""
import pytest
from agent_builder import (BuildCommand, BuildError, BuildHandler, Builder,
                           InMemoryAgentSpecStore)
from test_engine import Registry, manifest, task

class FakeSnapshotPort:
    def __init__(self, snapshot): self.snapshot = snapshot
    def ready_snapshot(self, tenant_id, snapshot_id):
        if (tenant_id, snapshot_id) != (self.snapshot.tenant_id, self.snapshot.task_snapshot_id):
            return None
        return self.snapshot

def command(snapshot, idem='key'):
    return BuildCommand(build_id='build-1', tenant_id=snapshot.tenant_id,
        task_snapshot_id=snapshot.task_snapshot_id, idempotency_key=idem,
        capability_registry_revision='v1', model_route='mock-model',
        evaluation_policy_ref=snapshot.acceptance_policy_ref)

@pytest.mark.asyncio
async def test_same_build_key_idempotent_and_immutable():
    snapshot = task('catalog',['catalog'],['read'],['catalog:read'])
    store = InMemoryAgentSpecStore()
    handler = BuildHandler(Builder(Registry([
        manifest('catalog.lookup',['catalog'],['read'],['catalog:read'])]),
        frozenset({'mock-model'})),FakeSnapshotPort(snapshot),store)
    cmd = command(snapshot)
    result = await handler.build(cmd)
    assert result.status == 'ASSEMBLED'
    assert await handler.build(cmd) == result
    assert store.get(snapshot.tenant_id,result.agent_spec_ref).artifact_digest == result.agent_spec_digest
    assert store.get('other-tenant',result.agent_spec_ref) is None
    with pytest.raises(BuildError,match='BUILD_IDEMPOTENCY_CONFLICT'):
        await handler.build(cmd.model_copy(update={'build_id':'different'}))

@pytest.mark.asyncio
async def test_missing_authority_or_tools_is_blocked():
    snapshot = task('catalog',['catalog'],['read'],['catalog:read'])
    handler = BuildHandler(Builder(Registry([]),frozenset({'mock-model'})),
                           FakeSnapshotPort(snapshot),InMemoryAgentSpecStore())
    wrong = await handler.build(command(snapshot).model_copy(update={'tenant_id':'intruder'}))
    assert wrong.status == 'BLOCKED'
    assert wrong.error_code == 'SNAPSHOT_NOT_READY_OR_DENIED'
    missing = await handler.build(command(snapshot,idem='key-new'))
    assert missing.status == 'BLOCKED' and missing.error_code == 'CAPABILITY_DENIED'
