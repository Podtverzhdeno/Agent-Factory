"""Optional REAL PostgreSQL replay test (dedicated sandbox DSN)."""
import os
from uuid import uuid4

import pytest
from agent_runtime.postgres_effects import PostgresEffectLedger

from agent_builder import digest
from agent_runtime import RuntimeDenied


@pytest.mark.asyncio
async def test_real_postgres_effect_reservation_survives_new_connections():
    pytest.importorskip('psycopg')
    dsn = os.getenv('AGENT_ENGINE_TEST_PG_DSN')
    if not dsn:
        pytest.skip('AGENT_ENGINE_TEST_PG_DSN required; never use production DB')
    key = digest({'integration_id':str(uuid4()), 'effect':'synthetic-draft'})
    first = PostgresEffectLedger(dsn)
    await first.setup()
    await first.reserve(key)
    assert await PostgresEffectLedger(dsn).status(key) == 'UNCERTAIN'
    with pytest.raises(RuntimeDenied, match='EFFECT_REPLAY_REQUIRES_RECONCILIATION'):
        await PostgresEffectLedger(dsn).reserve(key)
    await first.finish(key, {'artifact_ref':'artifact://synthetic/draft'})
    assert await PostgresEffectLedger(dsn).status(key) == 'CONFIRMED'
    with pytest.raises(RuntimeDenied, match='EFFECT_REPLAY_REQUIRES_RECONCILIATION'):
        await PostgresEffectLedger(dsn).reserve(key)
