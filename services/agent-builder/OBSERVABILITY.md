# Agent Engine — structured operational audit (v1)

This audit is **observability metadata**, not authoritative evidence of a
customer transaction and not the signed Runtime→Evaluation business artifact.

## Supported emissions

Events are JSON objects with the fixed `schema: "agent.audit.v1"`:

| Component | Events | When |
|---|---|---|
| `builder` | `build.started`, `build.finished`, `build.replayed`, `build.denied` | Commands, successful/blocked assembly, idempotency and failure |
| `runtime` | `run.started`, `run.finished`, `run.replayed`, `run.denied` | Direct Runtime **and** LangGraph orchestration |
| `tool` | `tool.started`, `tool.finished`, `tool.denied` | Attempted invocation of an approved tool at the ToolGateway boundary |
| `a2a` | `a2a.denied` | HTTP 401/403 returned by the isolated official A2A ASGI boundary |

Fields: `event`, `component`, `outcome`, `schema`, and optional
`code`, `duration_ms`, `steps`, `effect_count`. When a strong
HMAC key is configured, optional **pseudonymous** `tenant_tag`,
`operation_tag`, `trace_tag`, and `tool_tag` allow same-key correlation.
The tags are domain-separated and truncated SHA-256 HMACs, **not** raw IDs.

`BuildResult.status="ASSEMBLED"` is mapped to log
`outcome="COMPLETED"`, while blocked assemblies emit `BLOCKED`.
The audit event is never the durable commit or authorization proof.

## Enabling JSONL in an isolated app

To emit one raw JSON object per stdout line, set the app process environment:

- `AGENT_AUDIT_JSON_STDOUT=1`
- `AGENT_AUDIT_HMAC_KEY`: random, secret **at least 32 bytes**; set through
  the service's secret manager, never in code, image, README, or Git.
  The source process may omit it: in that case **no user ID or derived tag**
  is logged, and the audit still contains event/status/error metrics.

`AGENT_AUDIT_JSON_STDOUT` is opt-in; an app with an existing structured
Python logging collector can use `agent_factory.audit` at `INFO` instead.
The logger installs its own stdout handler at most once when enabled.
Do not enable a second collector for the same logger without deduplication.
Railway supplies an ingestion timestamp; payloads have no self-asserted
external wall-clock timestamp.

Example **shape only** (not an actual run):

```json
{"schema":"agent.audit.v1","component":"runtime","event":"run.finished","outcome":"BLOCKED","code":"BUDGET_EXCEEDED","steps":3,"duration_ms":176,"effect_count":0}
```

## Security invariants and review

The log producer intentionally **never** emits: prompts, model completions,
RFQ/document contents, tool arguments or outputs, bearer tokens, API keys,
signing keys, URLs, tool result artifacts, raw tenant/agent/run/trace IDs,
identity claims, principal names, exception text, stack traces, or client HTTP
headers. Only allowlisted event/outcome names and valid error codes appear.
Unexpected exceptions become `UNEXPECTED_*_EXCEPTION`; invalid error codes
become `REDACTED`.

HMAC tags are **pseudonymous, not anonymous**. Access should be restricted,
retention limited, and the secret rotated in line with security policy.
The log sink is best-effort: failure cannot replay a tool side effect or
change the business result. For strict financial audit obligations use a
separate durable, tamper-evident outbox and verified signed artifacts.

The Runtime/Evaluation Ed25519 pathway is separately versioned; it does
not accept operational JSONL records as successful signed execution evidence.

## Test coverage

- `test_structured_audit.py`: JSON allowlisting, no-secret behavior,
  weak-key denial, HMAC domain separation, key rotation, malicious error
  code redaction, bounded metrics, sink failure, builder success/conflict,
  runtime replay and denied tool args, ASGI auth denial.
- `test_audit_graph.py`: opt-in JSONL stdout in a real subprocess,
  no-key mode, LangGraph durable replay and denied run telemetry.
- All tests run in both credential-free and strict ephemeral PostgreSQL
  phases in the isolated Railway `agent04-integration-gate`.

## Scope and limitations

The current branch is a candidate implementation under PR #3, not
production admission. This event stream does **not** prove complete
buyer↔supplier negotiation, cross-process exactly-once, evidence issuer
authenticity, KMS correctness or independent security acceptance.
