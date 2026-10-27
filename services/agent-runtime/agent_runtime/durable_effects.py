"""Durable SQLite effect ledger for isolated tests, NOT production PostgreSQL.

Reserve *before* dispatch; uncertain and confirmed keys both block further calls.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .core import RuntimeDenied


class SqliteEffectLedger:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = asyncio.Lock()
        with closing(self._connect()) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS effect_ledger (
                effect_key TEXT PRIMARY KEY,
                state TEXT NOT NULL CHECK(state IN ('UNCERTAIN','CONFIRMED')),
                result_json TEXT
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.execute('PRAGMA busy_timeout=15000')
        connection.execute('PRAGMA journal_mode=WAL')
        return connection

    async def reserve(self, key: str) -> None:
        async with self._lock:
            with closing(self._connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                try:
                    db.execute('INSERT INTO effect_ledger (effect_key, state) VALUES (?, ?)',
                               (key, 'UNCERTAIN'))
                except sqlite3.IntegrityError as exc:
                    db.execute('ROLLBACK')
                    raise RuntimeDenied('EFFECT_REPLAY_REQUIRES_RECONCILIATION') from exc
                db.execute('COMMIT')

    async def finish(self, key: str, result: dict) -> None:
        async with self._lock:
            with closing(self._connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                cursor = db.execute('UPDATE effect_ledger SET state=?, result_json=? '
                                    'WHERE effect_key=? AND state=?',
                                    ('CONFIRMED', json.dumps(result), key, 'UNCERTAIN'))
                if cursor.rowcount != 1:
                    db.execute('ROLLBACK')
                    raise RuntimeDenied('INVALID_EFFECT_TRANSITION')
                db.execute('COMMIT')

    def status(self, key: str) -> str | None:
        with closing(self._connect()) as db:
            row = db.execute('SELECT state FROM effect_ledger WHERE effect_key=?', (key,)).fetchone()
            return row[0] if row else None
