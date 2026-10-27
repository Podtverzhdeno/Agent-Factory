"""Opt-in REAL PostgreSQL integration; never connect to production databases.

Requires AGENT_FACTORY_TEST_POSTGRES_DSN pointing to a *_test database and
AF_QUALITY_ALLOW_POSTGRES_IT=YES. Skipped (not PASSED) if absent.
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from quality_engine.core import Case, Dataset, EvaluationRequest, Principal
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata as jobs_meta
from quality_engine.sql_vault import SqlDatasetVault, metadata as gold_meta


def test_postgres_gold_and_job_recovery():
    dsn = os.getenv("AGENT_FACTORY_TEST_POSTGRES_DSN")
    if not dsn or os.getenv("AF_QUALITY_ALLOW_POSTGRES_IT") != "YES":
        pytest.skip("real PostgreSQL DSN and explicit integration consent required")
    url = make_url(dsn)
    if not url.drivername.startswith("postgresql") or not str(url.database).endswith("_test"):
        pytest.fail("integration connection must target dedicated PostgreSQL *_test database")
    pytest.importorskip("psycopg")
    schema = "af_eval_" + uuid.uuid4().hex[:12]
    admin = create_engine(dsn)
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        test_engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
        try:
            jobs_meta.create_all(test_engine)
            gold_meta.create_all(test_engine)
            owner = Principal("pg-tenant", "evaluation")
            vault = SqlDatasetVault(test_engine)
            vault.register(owner, Dataset("pg-tenant", "holdout-v1", "holdout",
                                          (Case("case", {"ok": True}, input_ref="artifact://case"),)))
            store = SqlEvaluationJobStore(test_engine)
            request = EvaluationRequest("pg-tenant", "spec", "sha256:spec",
                                        "holdout-v1", "policy", "idem", "run")
            assert store.submit(owner, request).status == "QUEUED"
            claim = store.claim(owner, run_id="run", worker_id="w1", now=0, lease_seconds=10)
            assert claim.attempt == 1
            resumed = SqlEvaluationJobStore(test_engine).claim(
                owner, run_id="run", worker_id="w2", now=12)
            assert resumed.attempt == 2
            assert SqlDatasetVault(test_engine).read(owner, "holdout-v1").cases[0].expected_artifact == {"ok": True}
            assert store.block_exhausted(owner, now=13, max_attempts=2) == 0
        finally:
            test_engine.dispose()
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()
