"""SQLite terminal-run result store for isolated crash/restart tests.

NOT a LangGraph checkpointer, not a production schema. Production DB ownership,
retention and transactional outbox require ratified ADR-0002.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from .core import RunResult, RuntimeDenied


class SqliteRunStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with closing(self._open()) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS agent04_run_results (
                tenant TEXT NOT NULL,
                run_id TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                result_json TEXT NOT NULL,
                PRIMARY KEY (tenant, run_id)
            )""")

    def _open(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.execute('PRAGMA busy_timeout=15000')
        return db

    def load(self, tenant: str, run_id: str) -> tuple[str, RunResult] | None:
        with closing(self._open()) as conn:
            row = conn.execute('SELECT request_hash, result_json FROM agent04_run_results '
                               'WHERE tenant=? AND run_id=?',(tenant,run_id)).fetchone()
        if row is None:
            return None
        payload = json.loads(row[1])
        payload['tool_effect_refs'] = tuple(payload['tool_effect_refs'])
        return row[0], RunResult(**payload)

    def save(self, tenant: str, run_id: str, request_hash: str, result: RunResult) -> None:
        if not request_hash.startswith('sha256:') or len(request_hash) != 71:
            raise RuntimeDenied('INVALID_RUN_HASH')
        raw = json.dumps(asdict(result), ensure_ascii=True, allow_nan=False)
        with closing(self._open()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            cursor = conn.execute('SELECT request_hash, result_json FROM agent04_run_results '
                                  'WHERE tenant=? AND run_id=?',(tenant,run_id))
            old = cursor.fetchone()
            if old is not None:
                conn.execute('ROLLBACK')
                if old[0] != request_hash or old[1] != raw:
                    raise RuntimeDenied('RUN_IDEMPOTENCY_CONFLICT')
                return
            conn.execute('INSERT INTO agent04_run_results VALUES(?,?,?,?)',
                         (tenant,run_id,request_hash,raw))
            conn.execute('COMMIT')
