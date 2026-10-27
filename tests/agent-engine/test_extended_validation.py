"""Hardening regressions: version correctness and model argument trust boundary."""

import pytest

from agent_builder import BuildError, Builder
from agent_runtime import EffectLedger, RuntimeDenied, ToolPolicy, VerifiedToolGateway
from test_engine import FakeTools, Registry, build, manifest, task


def test_full_task_snapshot_is_part_of_agent_version():
    reg = Registry([manifest('approved-read', ['read'], ['read'], ['read'])])
    original = task('read', ['read'], ['read'], ['read'])
    a = build(original, reg)
    changed = original.model_copy(update={'objective': 'Another customer authorized use case'})
    b = build(changed, reg)
    assert a.agent_spec_version != b.agent_spec_version
    assert a.a2a_card_ref != b.a2a_card_ref
    assert a.verify_digest() and b.verify_digest()


def test_empty_side_effect_manifest_cannot_be_selected():
    reg = Registry([manifest('missing-effect-declaration', ['read'], [], ['read'])])
    with pytest.raises(BuildError, match='CAPABILITY_DENIED'):
        build(task('read', ['read'], ['read'], ['read']), reg)


@pytest.mark.asyncio
@pytest.mark.parametrize('args,error', [
    ({'outer': {'api_key': 'should-never-cross'}}, 'CREDENTIAL_IN_TOOL_ARGS'),
    ({'batch': [{'headers': {'authorization': 'Bearer anything'}}]}, 'CREDENTIAL_IN_TOOL_ARGS'),
    ({'f': float('nan')}, 'INVALID_TOOL_ARGS'),
    ({'nested': [{1: 'not-json'}]}, 'INVALID_TOOL_ARGS'),
    ({'nested': ['é' * 16000]}, 'INVALID_TOOL_ARGS'),
    ({'headers': {'X-API-Key': 'not allowed'}}, 'CREDENTIAL_IN_TOOL_ARGS')
])
async def test_nested_secrets_invalid_json_and_oversize_are_denied_before_call(args, error):
    spec = build(task('draft', ['draft'], ['draft_file'], ['draft:write']),
                 Registry([manifest('render', ['draft'], ['draft_file'], ['draft:write'])]))
    binding = spec.selected_tools[0]
    tools = FakeTools()
    policy = ToolPolicy(tenant_id=spec.tenant_id, tool_id=binding.tool_id,
        version=binding.version, manifest_digest=binding.digest,
        scopes=frozenset(binding.granted_scopes), effect_mode='draft_file',
        input_schema={'type': 'object'}, output_schema={'type': 'object'})
    gateway = VerifiedToolGateway(tools, EffectLedger(), policies={'render': policy})
    with pytest.raises(RuntimeDenied, match=error):
        await gateway.execute(spec, binding, args=args, run_id='r', step=1)
    assert not tools.called


def test_snapshot_hash_is_deterministic_across_process_hash_seeds(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([
        str(root / 'services' / 'agent-builder'),
        str(root / 'services' / 'agent-runtime'), str(root / 'tests' / 'agent-engine')])}
    script = '''
from agent_builder import Builder
from test_engine import Registry, manifest, build, task
one = task('purchase', ['catalog','supplier','review'], ['read'], ['catalog:read','supplier:read'])
reg = Registry([manifest('all', ['catalog','supplier','review'], ['read'], ['catalog:read','supplier:read'])])
spec = build(one, reg)
print(spec.agent_spec_version, spec.artifact_digest)
'''
    results=[]
    for seed in ('1', '2', '9999'):
        output = subprocess.check_output([sys.executable, '-c', script],
                                         env={**env,'PYTHONHASHSEED':seed},timeout=10)
        results.append(output.decode().strip())
    assert len(set(results)) == 1
