"""Postgres ledger refuses malformed results without touching the database."""

import pytest

from agent_runtime import RuntimeDenied
from agent_runtime.postgres_effects import PostgresEffectLedger


@pytest.mark.asyncio
@pytest.mark.parametrize('payload,error', [
    ({'value':float('nan')},'INVALID_EFFECT_RESULT'),
    ({'n':None,'x':object()},'INVALID_EFFECT_RESULT'),
    ({'text':'😬'*9000},'EFFECT_RESULT_TOO_LARGE'),
    ([], 'INVALID_EFFECT_RESULT'),
])
async def test_pg_ledger_rejects_invalid_output_before_importing_driver(payload,error):
    store = PostgresEffectLedger('postgresql://localhost:5432/synthetic')
    with pytest.raises(RuntimeDenied, match=error):
        await store.finish('sha256:' + 'f'*64, payload)
