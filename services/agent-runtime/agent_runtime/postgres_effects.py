"""Optional PostgreSQL effect ledger; use ONLY with isolated test DB.

Not a production migration or exactly-once guarantee. ADR-0002 must define DB
ownership, encryption, retention, reconciliation and outbox before deployment.
"""

from __future__ import annotations

import json

from .core import RuntimeDenied


class PostgresEffectLedger:
    def __init__(self, dsn: str):
        if not dsn or not dsn.startswith(('postgresql://', 'postgres://')):
            raise ValueError('PostgreSQL connection string required')
        self._dsn = dsn

    async def _connect(self):
        try:
            from psycopg import AsyncConnection
        except ImportError as exc:
            raise RuntimeError('psycopg3 is required') from exc
        return await AsyncConnection.connect(self._dsn, connect_timeout=5)

    async def setup(self) -> None:
        """Only for disposable sandbox DB; schema is not owner-ratified."""
        async with await self._connect() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS agent04_candidate_effect_ledger (
                effect_key TEXT PRIMARY KEY,
                state TEXT NOT NULL CHECK (state IN ('UNCERTAIN', 'CONFIRMED')),
                result_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    async def reserve(self, key: str) -> None:
        if not key.startswith('sha256:') or len(key) != 71:
            raise RuntimeDenied('INVALID_EFFECT_KEY')
        async with await self._connect() as conn:
            cursor = await conn.execute("""INSERT INTO agent04_candidate_effect_ledger
                (effect_key, state) VALUES (%s, 'UNCERTAIN')
                ON CONFLICT DO NOTHING RETURNING effect_key""", (key,))
            if await cursor.fetchone() is None:
                raise RuntimeDenied('EFFECT_REPLAY_REQUIRES_RECONCILIATION')

    async def finish(self, key: str, result: dict) -> None:
        if not isinstance(result, dict):
            raise RuntimeDenied('INVALID_EFFECT_RESULT')
        try:
            payload = json.dumps(result, ensure_ascii=False, allow_nan=False)
            size = len(payload.encode('utf-8'))
        except (TypeError, ValueError, RecursionError, UnicodeError, OverflowError) as exc:
            raise RuntimeDenied('INVALID_EFFECT_RESULT') from exc
        if size > 32768:
            raise RuntimeDenied('EFFECT_RESULT_TOO_LARGE')
        from psycopg.types.json import Jsonb
        async with await self._connect() as conn:
            cursor = await conn.execute("""UPDATE agent04_candidate_effect_ledger
                SET state='CONFIRMED', result_json=%s
                WHERE effect_key=%s AND state='UNCERTAIN'""", (Jsonb(result), key))
            if cursor.rowcount != 1:
                raise RuntimeDenied('INVALID_EFFECT_TRANSITION')

    async def status(self, key: str) -> str | None:
        async with await self._connect() as conn:
            cursor = await conn.execute('SELECT state FROM agent04_candidate_effect_ledger '
                                        'WHERE effect_key=%s', (key,))
            row = await cursor.fetchone()
            return row[0] if row else None
