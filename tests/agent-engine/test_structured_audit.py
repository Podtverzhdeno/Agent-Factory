"""Structured audit regression tests: privacy, idempotency, tenant and failures."""

import json
import logging

import httpx
import pytest
from agent_builder import Builder, BuildError, BuildHandler, InMemoryAgentSpecStore
from agent_builder.audit import audit_event
from agent_runtime import Decision, RuntimeDenied
from test_a2a_security import make_app
from test_build_handler import FakeSnapshotPort, command
from test_engine import Registry, build, invoke, manifest, task

LOGGER = "agent_factory.audit"
SECRET = "secret-bearer-DO-NOT-LOG-0123456789"


def _records(caplog):
    return [json.loads(r.message) for r in caplog.records if r.name == LOGGER]


def test_audit_default_never_emits_raw_identifiers_or_content(caplog, monkeypatch):
    monkeypatch.delenv("AGENT_AUDIT_HMAC_KEY", raising=False)
    with caplog.at_level(logging.INFO, logger=LOGGER):
        audit_event("runtime", "run.finished", "BLOCKED", tenant_id=SECRET,
                    operation_id=SECRET, trace_id=SECRET, tool_id=SECRET,
                    code="INVALID_TOOL_ARGS", duration_ms=12, steps=2,
                    effect_count=0)
    row = _records(caplog)[0]
    assert row == {
        "schema": "agent.audit.v1", "component": "runtime",
        "event": "run.finished", "outcome": "BLOCKED",
        "code": "INVALID_TOOL_ARGS", "duration_ms": 12,
        "steps": 2, "effect_count": 0,
    }
    assert SECRET not in caplog.text


@pytest.mark.parametrize("key", ["", "short", "x" * 31])
def test_audit_weak_or_missing_key_omits_pseudonymous_identifiers(
    caplog, monkeypatch, key,
):
    monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", key)
    with caplog.at_level(logging.INFO, logger=LOGGER):
        audit_event("builder", "build.started", "STARTED",
                    tenant_id=SECRET, operation_id=SECRET, trace_id=SECRET)
    row = _records(caplog)[0]
    assert all(name not in row for name in ("tenant_tag", "operation_tag", "trace_tag"))


def test_audit_hmac_tags_correlate_only_with_correct_domain(caplog, monkeypatch):
    monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "random-example-key-DO-NOT-USE-in-production-012345")
    with caplog.at_level(logging.INFO, logger=LOGGER):
        audit_event("runtime", "run.started", "STARTED", tenant_id=SECRET,
                    operation_id=SECRET, trace_id=SECRET, tool_id=SECRET)
        audit_event("runtime", "run.finished", "COMPLETED", tenant_id=SECRET,
                    operation_id=SECRET, trace_id=SECRET, tool_id=SECRET)
    rows = _records(caplog)
    for field in ("tenant_tag", "operation_tag", "trace_tag", "tool_tag"):
        assert rows[0][field] == rows[1][field]
        assert len(rows[0][field]) == 24
    assert len({rows[0][field] for field in (
        "tenant_tag", "operation_tag", "trace_tag", "tool_tag")}) == 4
    assert SECRET not in caplog.text
    assert "random-example-key" not in caplog.text


def test_audit_different_keys_do_not_correlate(caplog, monkeypatch):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "A" * 32)
        audit_event("runtime", "run.started", "STARTED", tenant_id="buyer")
        monkeypatch.setenv("AGENT_AUDIT_HMAC_KEY", "B" * 32)
        audit_event("runtime", "run.started", "STARTED", tenant_id="buyer")
    first, second = _records(caplog)
    assert first["tenant_tag"] != second["tenant_tag"]


@pytest.mark.parametrize("code,expected", [
    ("BUDGET_EXCEEDED", "BUDGET_EXCEEDED"),
    ("TOOL_TIMEOUT_UNCERTAIN", "TOOL_TIMEOUT_UNCERTAIN"),
    ("JWT\n" + SECRET, "REDACTED"),
    ("bad-code", "REDACTED"),
    (SECRET, "REDACTED"),
    ("A" * 80, "REDACTED"),
])
def test_error_codes_cannot_inject_log_fields(caplog, code, expected):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        audit_event("runtime", "run.denied", "DENIED", code=code)
    assert _records(caplog)[0]["code"] == expected
    assert SECRET not in caplog.text


@pytest.mark.parametrize("event,component,outcome", [
    ("other.event", "runtime", "STARTED"),
    ("run.started", "fake-component", "STARTED"),
    ("run.started", "runtime", "USER_SUPPLIED"),
])
def test_unknown_event_enums_cannot_enter_audit(caplog, event, component, outcome):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        audit_event(component, event, outcome)
    assert _records(caplog) == []


@pytest.mark.parametrize("duration,steps,effects", [
    (-1, 1, 1),
    (float("nan"), 1, 1),
    (10_000_001, 1, 1),
])
def test_invalid_metric_values_are_never_recorded(caplog, duration, steps, effects):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        audit_event("runtime", "run.finished", "COMPLETED",
                    duration_ms=duration, steps=steps, effect_count=effects)
    assert "duration_ms" not in _records(caplog)[0]


def test_audit_sink_failure_does_not_block_a_business_action(monkeypatch):
    from agent_builder.audit import LOGGER as audit_logger

    monkeypatch.setattr(audit_logger, "isEnabledFor", lambda level: True)

    def unavailable(message):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(audit_logger, "info", unavailable)
    # Even an unavailable sink must not retry or fail a consequential action.
    audit_event("tool", "tool.finished", "COMPLETED", code="OK")


@pytest.mark.asyncio
async def test_builder_audits_success_replay_and_idempotency_conflict(caplog):
    snapshot = task("audit-build", ["catalog"], ["read"], ["catalog:read"])
    handler = BuildHandler(Builder(Registry([
        manifest("catalog.lookup", ["catalog"], ["read"], ["catalog:read"]),
    ]), frozenset({"mock-model"})),
        FakeSnapshotPort(snapshot), InMemoryAgentSpecStore())
    cmd = command(snapshot)
    with caplog.at_level(logging.INFO, logger=LOGGER):
        first = await handler.build(cmd)
        assert (await handler.build(cmd)) == first
        with pytest.raises(BuildError, match="BUILD_IDEMPOTENCY_CONFLICT"):
            await handler.build(cmd.model_copy(update={"build_id": SECRET}))
    events = [r["event"] for r in _records(caplog)]
    assert events.count("build.started") == 3
    assert events.count("build.finished") == 2
    assert "build.replayed" in events
    assert "build.denied" in events
    assert first.status == "ASSEMBLED"
    assert SECRET not in caplog.text
    assert "Complete approved synthetic" not in caplog.text


@pytest.mark.asyncio
async def test_builder_audits_blocked_policy_without_exception_details(caplog):
    snapshot = task("audit-deny", ["payment"], ["read"], [])
    handler = BuildHandler(Builder(Registry([]), frozenset({"mock-model"})),
                           FakeSnapshotPort(snapshot), InMemoryAgentSpecStore())
    with caplog.at_level(logging.INFO, logger=LOGGER):
        result = await handler.build(command(snapshot))
    assert result.status == "BLOCKED"
    finished = next(r for r in _records(caplog) if r["event"] == "build.finished")
    assert finished["outcome"] == "BLOCKED"
    assert finished["code"] == "CAPABILITY_DENIED"


@pytest.mark.asyncio
async def test_runtime_audits_start_success_and_duplicate_without_raw_prompt(caplog):
    spec = build(task("audit-run", ["read"], ["read"], ["catalog:read"]),
                 Registry([manifest("catalog.lookup", ["read"], ["read"], ["catalog:read"])]))
    runtime, tools = invoke(spec, [
        Decision(kind="tool", tool_id="catalog.lookup", args={"query": SECRET}),
        Decision(kind="final", text=SECRET),
    ])
    with caplog.at_level(logging.INFO, logger=LOGGER):
        first = await runtime.run(spec, tenant_id="buyer", run_id="audit-1",
                                  thread_id="thread", request=SECRET, trace_id=SECRET)
        duplicate = await runtime.run(spec, tenant_id="buyer", run_id="audit-1",
                                      thread_id="thread", request=SECRET, trace_id=SECRET)
    assert first == duplicate and first.status == "COMPLETED"
    assert len(tools.called) == 1
    events = [r["event"] for r in _records(caplog)]
    assert events.count("run.started") == 2
    assert events.count("run.finished") == 2
    assert events.count("run.replayed") == 1
    assert events.count("tool.started") == 1
    assert events.count("tool.finished") == 1
    assert SECRET not in caplog.text


@pytest.mark.asyncio
async def test_runtime_denial_and_tool_credential_rejection_are_audited(caplog):
    spec = build(task("audit-security", ["read"], ["read"], ["catalog:read"]),
                 Registry([manifest("catalog.lookup", ["read"], ["read"], ["catalog:read"])]))
    runtime, tools = invoke(spec, [Decision(kind="tool", tool_id="catalog.lookup",
                                           args={"nested": {"x-api-key": SECRET}})])
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with pytest.raises(RuntimeDenied, match="TENANT_DENIED"):
            await runtime.run(spec, tenant_id="attacker", run_id="denied",
                              thread_id="thread", request=SECRET, trace_id=SECRET)
        blocked = await runtime.run(spec, tenant_id="buyer", run_id="ok",
                                    thread_id="thread", request=SECRET, trace_id=SECRET)
    assert blocked.status == "BLOCKED" and blocked.error_code == "CREDENTIAL_IN_TOOL_ARGS"
    assert tools.called == []
    audit = _records(caplog)
    assert any(r["event"] == "run.denied" and r["code"] == "TENANT_DENIED" for r in audit)
    assert any(r["event"] == "tool.denied" and r["code"] == "CREDENTIAL_IN_TOOL_ARGS"
               for r in audit)
    assert any(r["event"] == "run.finished" and r["outcome"] == "BLOCKED" for r in audit)
    assert SECRET not in caplog.text


@pytest.mark.asyncio
async def test_a2a_denied_requests_emit_only_safe_status_code(caplog):
    app = make_app()
    with caplog.at_level(logging.INFO, logger=LOGGER):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://localhost") as client:
            unauth = await client.get("/", headers={"Authorization": "Bearer " + SECRET})
            assert unauth.status_code == 401
            revoked = await client.get("/", headers={"Authorization": "Bearer wrong-tenant"})
            assert revoked.status_code == 403
    audit = _records(caplog)
    assert [row["component"] for row in audit] == ["a2a", "a2a"]
    assert [row["code"] for row in audit] == ["A2A_UNAUTHENTICATED", "A2A_FORBIDDEN"]
    assert SECRET not in caplog.text
