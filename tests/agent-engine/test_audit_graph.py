"""Subprocess JSONL logging and durable graph run correlation checks."""

import json
import logging
import os
import subprocess
import sys

import pytest
from agent_runtime import RuntimeDenied
from agent_runtime.langgraph_adapter import invoke_graph
from test_langgraph_idempotency import FakeCompiledGraph, setup_runtime


def test_jsonl_stdout_optin_emits_one_redacted_event():
    script = (
        "from agent_builder.audit import audit_event; "
        "audit_event('runtime','run.finished','COMPLETED',"
        "tenant_id='raw-private-customer',"
        "operation_id='raw-private-run',trace_id='raw-private-trace',"
        "duration_ms=15,steps=3)"
    )
    env = dict(os.environ)
    env["AGENT_AUDIT_JSON_STDOUT"] = "1"
    env["AGENT_AUDIT_HMAC_KEY"] = "synthetic-only-32-or-more-bytes-key-for-tests"
    process = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True,
        text=True, check=False, timeout=15)
    assert process.returncode == 0
    rows = process.stdout.splitlines()
    assert len(rows) == 1
    data = json.loads(rows[0])
    assert data["schema"] == "agent.audit.v1"
    assert data["component"] == "runtime"
    assert data["event"] == "run.finished"
    assert data["duration_ms"] == 15
    assert data["steps"] == 3
    assert len(data["tenant_tag"]) == 24
    assert "raw-private" not in process.stdout
    assert "synthetic-only" not in process.stdout


def test_jsonl_stdout_without_hmac_key_exposes_no_user_identity():
    script = (
        "from agent_builder.audit import audit_event; "
        "audit_event('a2a','a2a.denied','DENIED',tenant_id='raw-secret-customer')"
    )
    env = dict(os.environ)
    env["AGENT_AUDIT_JSON_STDOUT"] = "1"
    env.pop("AGENT_AUDIT_HMAC_KEY", None)
    process = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True,
        text=True, check=False, timeout=15)
    assert process.returncode == 0
    row = json.loads(process.stdout.strip())
    assert row["event"] == "a2a.denied"
    assert "tenant_tag" not in row
    assert "raw-secret-customer" not in process.stdout


@pytest.mark.asyncio
async def test_durable_graph_audits_completion_cache_and_conflict(caplog, tmp_path):
    spec, runtime = setup_runtime(tmp_path)
    graph = FakeCompiledGraph()
    kwargs = {"tenant_id": "buyer", "thread_id": "t", "run_id": "r",
              "request": "private-document-value", "trace_id": "private-trace"}
    with caplog.at_level(logging.INFO, logger="agent_factory.audit"):
        result = await invoke_graph(graph, runtime, spec, **kwargs)
        same = await invoke_graph(graph, runtime, spec, **kwargs)
        with pytest.raises(RuntimeDenied, match="RUN_IDEMPOTENCY_CONFLICT"):
            await invoke_graph(graph, runtime, spec, **{
                **kwargs, "request": "private-document-changed"})
    assert same == result
    assert graph.calls == 1
    events = [json.loads(r.message) for r in caplog.records
              if r.name == "agent_factory.audit"]
    assert [r["event"] for r in events].count("run.started") == 3
    assert [r["event"] for r in events].count("run.finished") == 2
    assert [r["event"] for r in events].count("run.replayed") == 1
    assert [r["event"] for r in events].count("run.denied") == 1
    assert "private-document" not in caplog.text
    assert "private-trace" not in caplog.text


@pytest.mark.asyncio
async def test_invalid_graph_request_audits_only_error_code(caplog, tmp_path):
    spec, runtime = setup_runtime(tmp_path)
    graph = FakeCompiledGraph()
    with caplog.at_level(logging.INFO, logger="agent_factory.audit"), pytest.raises(
        RuntimeDenied, match="INVALID_RUN_INPUT"
    ):
        await invoke_graph(graph, runtime, spec, tenant_id="buyer", run_id="",
                           thread_id="t", request="private-input", trace_id="trace")
    assert graph.calls == 0
    events = [json.loads(r.message) for r in caplog.records
              if r.name == "agent_factory.audit"]
    assert events[-1]["event"] == "run.denied"
    assert events[-1]["code"] == "INVALID_RUN_INPUT"
    assert "private-input" not in caplog.text
