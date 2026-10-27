"""AF-REQ-012: real OS process exit after synthetic effect, then denied retry."""
import os
import subprocess
import sys
from pathlib import Path

def test_process_crash_does_not_repeat_external_effect(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    paths = [str(repo/'services'/'agent-builder'),str(repo/'services'/'agent-runtime')]
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(paths)}
    db, effect = str(tmp_path/'effects.db'), str(tmp_path/'external.log')
    script = '''
import asyncio, os, sys
from agent_runtime import SqliteEffectLedger, RuntimeDenied

async def main():
    ledger = SqliteEffectLedger(sys.argv[1])
    try:
        await ledger.reserve('tenant-a:run-1:step-1:draft-render')
    except RuntimeDenied as exc:
        if exc.code == 'EFFECT_REPLAY_REQUIRES_RECONCILIATION':
            sys.exit(0)
        sys.exit(2)
    # An external effect commits, then process dies BEFORE ledger.finish.
    with open(sys.argv[2], 'a', encoding='utf8') as f:
        f.write('external-effect-committed\\n')
    os._exit(77)

asyncio.run(main())
'''
    first = subprocess.run([sys.executable,'-c',script,db,effect],env=env,
                           capture_output=True,timeout=10,check=False)
    assert first.returncode==77, first.stderr.decode()
    second = subprocess.run([sys.executable,'-c',script,db,effect],env=env,
                            capture_output=True,timeout=10,check=False)
    assert second.returncode==0, second.stderr.decode()
    assert Path(effect).read_text().splitlines()==['external-effect-committed']
