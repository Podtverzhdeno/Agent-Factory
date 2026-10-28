"""Audit logging privacy and runtime decision event regression contracts."""
import json
import logging

import pytest

from agent_builder.audit import LOGGER, audit_event
from agent_runtime import Decision
from test_engine import Registry, build, invoke, manifest, task


class Records(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class BrokenHandler(logging.Handler):
    def emit(self, record):
        raise RuntimeError("log sink error: token=TOP_SECRET")


@pytest.fixture
def audit_records(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "z" * 64)
    monkeypatch.delenv("AGENT_AUDIT_JSON_STDOUT", raising=False)
    handler = Records()
    old_level, old_disabled, old_propagate = LOGGER.level, LOGGER.disabled, LOGGER.propagate
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.disabled = False
    LOGGER.propagate = False
    try:
        yield handler.messages
    finally:
        LOGGER.removeHandler(handler)
        LOGGER.setLevel(old_level)
        LOGGER.disabled = old_disabled
        LOGGER.propagate = old_propagate


def test_audit_tags_are_stable_but_do_not_expose_private_identifiers(audit_records):
    audit_event("runtime", "run.started", "STARTED", tenant_id="buyer-PRIVATE",
                operation_id="run-SECRET", trace_id="trace-SECRET", tool_id="tool-SECRET")
    audit_event("runtime", "run.started", "STARTED", tenant_id="buyer-PRIVATE",
                operation_id="run-SECRET", trace_id="trace-SECRET", tool_id="tool-SECRET")
    assert len(audit_records) == 2
    assert audit_records[0] == audit_records[1]
    event = json.loads(audit_records[0])
    for value in ("buyer-PRIVATE", "run-SECRET", "trace-SECRET", "tool-SECRET"):
        assert value not in audit_records[0]
    assert all(len(event[key]) == 24 for key in
               ("tenant_tag", "operation_tag", "trace_tag", "tool_tag"))
    assert len(set(event[key] for key in
                   ("tenant_tag", "operation_tag", "trace_tag", "tool_tag"))) == 4


def test_audit_weak_or_missing_key_omits_identifiers(audit_records, monkeypatch):
    monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "short")
    audit_event("a2a", "a2a.denied", "DENIED", tenant_id="private",
                operation_id="private", trace_id="private")
    event = json.loads(audit_records[-1])
    assert "tenant_tag" not in event
    assert "operation_tag" not in event
    assert "trace_tag" not in event


def test_audit_never_serializes_invalid_codes_or_messages(audit_records):
    audit_event("runtime", "model.denied", "FAILED",
                code="token=SECRET and document raw", steps=3,
                duration_ms=-1, effect_count=100_000_001)
    event = json.loads(audit_records[-1])
    assert event["code"] == "REDACTED"
    assert "SECRET" not in audit_records[-1]
    assert "duration_ms" not in event
    assert "effect_count" not in event
    assert event["steps"] == 3


def test_audit_rejects_unsupported_events_or_statuses(audit_records):
    audit_event("runtime", "model.raw_prompt", "STARTED")
    audit_event("runtime", "model.decided", "RAW_RESPONSE")
    assert audit_records == []


@pytest.mark.asyncio
async def test_runtime_decision_events_link_to_run_without_logging_prompt(
        audit_records, monkeypatch):
    monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "k" * 64)
    spec = build(task("read", ["read"], ["read"], ["read"]),
                 Registry([manifest("read.tool", ["read"], ["read"], ["read"])]))
    runtime, tools = invoke(spec, [
        Decision(kind="tool", tool_id="read.tool", args={"secret": "private-QUOTE"}),
        Decision(kind="final", text="private-ANSWER"),
    ])
    # Credential keys are denied before any external tool invocation.
    result = await runtime.run(spec, tenant_id="buyer", run_id="run-audit",
                               thread_id="thread", request="private-PROMPT",
                               trace_id="trace-audit")
    assert result.status == "BLOCKED"
    assert result.error_code == "CREDENTIAL_IN_TOOL_ARGS"
    assert tools.called == []
    rows = [json.loads(item) for item in audit_records]
    assert any(x["event"] == "model.decided" for x in rows)
    assert rows[0]["event"] == "run.started"
    assert rows[-1]["event"] == "run.finished"
    assert rows[-1]["code"] == "CREDENTIAL_IN_TOOL_ARGS"
    assert rows[0]["operation_tag"] == rows[-1]["operation_tag"]
    assert rows[0]["trace_tag"] == rows[-1]["trace_tag"]
    joined = "".join(audit_records)
    for secret in ("private-QUOTE", "private-PROMPT", "private-ANSWER"):
        assert secret not in joined


def test_audit_sink_failure_does_not_abort_or_repeat_execution(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "x" * 64)
    monkeypatch.delenv("AGENT_AUDIT_JSON_STDOUT", raising=False)
    bad = BrokenHandler()
    LOGGER.addHandler(bad)
    previous = LOGGER.level
    LOGGER.setLevel(logging.INFO)
    try:
        audit_event("runtime", "run.started", "STARTED", operation_id="id")
    finally:
        LOGGER.removeHandler(bad)
        LOGGER.setLevel(previous)
