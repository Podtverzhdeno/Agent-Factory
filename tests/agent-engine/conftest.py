import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'services'
for name in ('agent-builder', 'agent-runtime', 'litellm-adapter'):
    sys.path.insert(0, str(ROOT / name))

def pytest_sessionfinish(session, exitstatus):
    """Integration acceptance MUST fail rather than silently skip official SDK tests."""
    import os

    import pytest
    if os.getenv('AGENT_ENGINE_REQUIRE_INTEGRATIONS') != '1':
        return
    reporter = session.config.pluginmanager.get_plugin('terminalreporter')
    skipped = reporter.stats.get('skipped', []) if reporter else []
    if skipped:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
