"""Privacy-minimal JSON audit events for Builder, Runtime and A2A.

No prompts, document contents, credentials, exception messages or raw IDs.
Identifiers are logged only as HMAC tags when configured with a strong secret.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sys
import threading
from typing import Literal

LOGGER = logging.getLogger("agent_factory.audit")
_CONFIG_LOCK = threading.Lock()


def enable_json_audit_stdout() -> None:
    """Opt-in JSONL stdout handler, idempotent even with concurrent runs."""
    with _CONFIG_LOCK:
        if any(handler.name == "agent_factory.audit.jsonl.v1" for handler in LOGGER.handlers):
            return
        handler = logging.StreamHandler(sys.stdout)
        handler.set_name("agent_factory.audit.jsonl.v1")
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
        LOGGER.setLevel(logging.INFO)
        LOGGER.propagate = False

_COMPONENTS = frozenset({"builder", "runtime", "tool", "a2a"})
_EVENTS = frozenset({
    "build.started", "build.finished", "build.replayed", "build.denied",
    "run.started", "run.finished", "run.replayed", "run.denied",
    "tool.started", "tool.finished", "tool.denied", "a2a.denied",
})
_OUTCOMES = frozenset({"STARTED", "COMPLETED", "BLOCKED", "REPLAYED", "DENIED", "FAILED"})
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

def _tag(kind: str, value: str | None, key: str) -> str | None:
    """Domain-separated, keyed pseudonyms; absent for weak/unconfigured keys."""
    if not value or not key or len(key.encode("utf-8")) < 32:
        return None
    msg = (kind + "\x00" + value).encode("utf-8")
    return hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:24]


def audit_event(
    component: Literal["builder", "runtime", "tool", "a2a"],
    event: str,
    outcome: str,
    *,
    tenant_id: str | None = None,
    operation_id: str | None = None,
    trace_id: str | None = None,
    tool_id: str | None = None,
    code: str | None = None,
    duration_ms: int | None = None,
    steps: int | None = None,
    effect_count: int | None = None,
) -> None:
    """Emit one bounded JSON record; never propagate telemetry sink failures.

    Nothing from exceptions or tool payloads is interpolated into the record.
    Trace tags are pseudonymous, not anonymous, and should be retained briefly.
    """
    if os.environ.get("AGENT_AUDIT_JSON_STDOUT") == "1":
        enable_json_audit_stdout()
    if not LOGGER.isEnabledFor(logging.INFO):
        return
    if component not in _COMPONENTS or event not in _EVENTS or outcome not in _OUTCOMES:
        return
    data: dict[str, str | int] = {
        "schema": "agent.audit.v1",
        "component": component,
        "event": event,
        "outcome": outcome,
    }
    if code is not None:
        data["code"] = code if _CODE.fullmatch(code) else "REDACTED"
    for name, value in (
        ("duration_ms", duration_ms),
        ("steps", steps),
        ("effect_count", effect_count),
    ):
        if type(value) is int and 0 <= value <= 10_000_000:
            data[name] = value
    key = os.environ.get("AGENT_AUDIT_HMAC_KEY", "")
    for name, domain, value in (
        ("tenant_tag", "tenant", tenant_id),
        ("operation_tag", "operation", operation_id),
        ("trace_tag", "trace", trace_id),
        ("tool_tag", "tool", tool_id),
    ):
        tag = _tag(domain, value, key)
        if tag is not None:
            data[name] = tag
    try:
        LOGGER.info(json.dumps(data, separators=(",", ":"), sort_keys=True))
    except Exception:  # noqa: BLE001 - failed observability must not replay side effects.
        return
