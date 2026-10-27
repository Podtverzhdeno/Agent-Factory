"""Tenant-scoped SQLite memory for synthetic tests; plaintext, not production."""
from __future__ import annotations
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Callable
from .core import RuntimeDenied

class SqliteMemory:
    def __init__(self, path: str | Path, clock: Callable[[], float] = time.time):
        self.path = str(path)
        self.clock = clock
        with closing(self._open()) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS thread_memory (
              tenant TEXT NOT NULL, agent TEXT NOT NULL, thread TEXT NOT NULL,
              position INTEGER NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(tenant, agent, thread, position))''')
            db.execute('''CREATE TABLE IF NOT EXISTS scoped_memory (
              tenant TEXT NOT NULL, agent TEXT NOT NULL, name TEXT NOT NULL,
              valid_until REAL NOT NULL, value TEXT NOT NULL,
              PRIMARY KEY(tenant, agent, name))''')

    def _open(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.execute('PRAGMA busy_timeout=15000')
        return db

    def get(self, tenant: str, agent: str, thread: str) -> list[dict]:
        with closing(self._open()) as db:
            rows = db.execute('SELECT payload FROM thread_memory WHERE tenant=? AND agent=? '
                              'AND thread=? ORDER BY position DESC LIMIT 50', (tenant, agent, thread))
            return [json.loads(row[0]) for row in reversed(list(rows))]

    def append(self, tenant: str, agent: str, thread: str, entry: dict):
        content = json.dumps(entry, ensure_ascii=False)
        if len(content) > 16000:
            raise RuntimeDenied('MEMORY_TOO_LARGE')
        with closing(self._open()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO thread_memory VALUES (?, ?, ?, '
                       'COALESCE((SELECT MAX(position)+1 FROM thread_memory '
                       'WHERE tenant=? AND agent=? AND thread=?), 0), ?)',
                       (tenant, agent, thread, tenant, agent, thread, content))
            db.execute('COMMIT')

    def put(self, tenant: str, agent: str, key: str, text: str, *, ttl_seconds: int):
        if ttl_seconds <= 0 or len(text) > 10000:
            raise RuntimeDenied('MEMORY_POLICY_DENIED')
        with closing(self._open()) as db:
            db.execute('INSERT INTO scoped_memory VALUES (?, ?, ?, ?, ?) '
                       'ON CONFLICT(tenant,agent,name) DO UPDATE SET '
                       'valid_until=excluded.valid_until,value=excluded.value',
                       (tenant, agent, key, self.clock() + ttl_seconds, text))

    def get_long(self, tenant: str, agent: str, key: str) -> str | None:
        with closing(self._open()) as db:
            result = db.execute('SELECT valid_until, value FROM scoped_memory '
                                'WHERE tenant=? AND agent=? AND name=?',
                                (tenant, agent, key)).fetchone()
            if result is None or result[0] <= self.clock():
                return None
            return result[1]

    def purge_expired(self) -> int:
        """Physically remove expired memory; does not promise cryptographic erasure."""
        with closing(self._open()) as db:
            cursor = db.execute('DELETE FROM scoped_memory WHERE valid_until<=?',
                                (self.clock(),))
            return cursor.rowcount
