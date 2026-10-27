# Agent Engine 04 — implementation and acceptance evidence

**Status:** ISOLATED COMPONENT IMPLEMENTATION. **Do not merge/release** until
owner ADR-0002 and independent integration/quality gates are satisfied.
**Branch:** `agent/04-agent-engine`; **target:** `docs/sdd-foundation-mvp`.
No shared OpenSpec, ADR, other agents' directories or production infrastructure changed.

## Requirement → tests

| Requirement | Candidate implementation | Evidence |
| --- | --- | --- |
| AF-REQ-005/006/029 | READY snapshot + BuildCommand, immutable versioned AgentSpec, deterministic minimum approved coverage, least-risk/grants tie-break, tenant-scoped idempotent BuildHandler | `test_build_handler.py`, `test_engine.py` |
| AF-REQ-007/016 | bounded ReAct candidate runtime, two different synthetic tasks, real generated RFQ XLSX and read-only supplier check | `test_engine.py`, `test_synthetic_demo.py`, `test_limits.py`, `test_security_authority.py` |
| AF-REQ-012 | SQLite synthetic durable effect reservations, replay conflict and process-kill test; optional PostgreSQL transactional reservation + test | `test_durable_security.py`, `test_process_restart.py`, `test_postgres_effects.py`, `test_langgraph_idempotency.py` |
| AF-REQ-013 | authenticated ASGI/A2A boundary with dynamic release-revocation check; official SDK v1 route/client test (optional) | `test_a2a_security.py`, `test_official_integrations.py` |
| AF-REQ-023 | LiteLLM-compatible allowlisted model adapter; proxy-side token injection, authoritative cost header, max-output limit, model timeout | `test_litellm.py`, `test_limits.py` |
| AF-REQ-039/040/042/043 | LangGraph graph adapter, tenant/version-scoped checkpoint identity, SQLite thread/long-term TTL memory, optional AsyncPostgresSaver reopened-connection test | `test_langgraph_boundary.py`, `test_official_integrations.py`, `test_durable_security.py` |

## Actual local evidence (Python 3.13)

- `python -m pytest -q tests/agent-engine -ra`: **88 passed, 4 skipped**.
- `python -m compileall -q services tests`: completed.
- `pytest --cov=agent_builder --cov=agent_runtime --cov=litellm_adapter`:
  82% aggregate coverage, mostly optional integrations absent.
- `AGENT_ENGINE_REQUIRE_INTEGRATIONS=1 python -m pytest -q tests/agent-engine/test_official_integrations.py -k real_langgraph -ra`:
  **exit code 1** on skipped SDK test; verified fail-closed integration gate.
- GitHub SDD workflow checks specification, **not** the full Agent Engine test suite.

## Reproduce

Component only, synthetic data:
```bash
python -m pip install -r tests/agent-engine/requirements.txt
python -m pytest -q tests/agent-engine -ra
```

Full acceptance (provision isolated PostgreSQL, never production):
```bash
python -m pip install -r tests/agent-engine/requirements-integration.txt
export AGENT_ENGINE_TEST_PG_DSN='postgresql://user:***@localhost:5432/agent04_test'
bash tests/agent-engine/run_integration_gates.sh
```
Integration script requires Ruff, Pyright, official LangGraph/A2A SDK and PostgreSQL.
**Any skipped test fails acceptance**. The integration script is supplied but
**not yet executed successfully**. This environment has no network/package
access for the missing dependencies and no disposable PostgreSQL.

## Architectural boundaries

- Builder accepts only externally READY task and Registry-issued approved tools.
  It never creates grants, fetches sealed holdouts or installs MCP servers.
- Runtime and Builder expose typed ports; mocks are separate from production
  adapters. The same factory code generates distinct AgentSpecs by configuration.
- `AgentSpec.artifact_digest` provides content integrity **not authenticity**.
  Owner-approved signing, trusted artifact storage and canonical schema contracts
  must precede release. No credentials in the spec or system prompt.
- A2A official SDK adapter constructs routes *only* for released/pinned versions,
  behind a bearer identity resolver. Its dynamic release lookup prevents stale
  release snapshots. Malformed resolvers and authorization outages fail closed.
  Full SDK conformance is **not verified**.
- MCP calls use explicit injected read-only transport and verified schema/scopes;
  remote MCP never grants authority and cannot dispatch consequential writes.
- LiteLLM HTTP adapter reads `x-litellm-response-cost` or mock `usage.cost`.
  Production quota requires centralized LiteLLM Proxy with database-backed
  spend controls, configured by integration owner; local response accounting is
  not a hard dollar ceiling before provider execution.

## Side-effect, privacy and security limitations

- Persist external effect reservation BEFORE executing a draft; an ambiguous
  outcome remains UNCERTAIN, and replay is DENIED pending reconciliation.
  A ReAct step has one stable effect slot (tenant + agent + run + step);
  changed LLM arguments or a different tool at the same step cannot sidestep
  the replay reservation.
  SQLite tests demonstrate a real process termination. A PostgreSQL candidate
  ledger is provided but not run against a real database.
- No exactly-once guarantee: external tools must honor durable idempotency keys,
  and reconciliation/outbox must be implemented at the approved boundary.
- SQLite checkpoints/memory/run store are isolated plaintext synthetic fixtures:
  tenant/agent/thread isolation, bounded context and TTL covered by tests.
  Candidate LangGraph invocations use the same saved terminal-run result so a
  repeated run ID does not replay a completed graph.
  Production encryption, TTL sweeper, right-to-delete and data retention pending.
- Tool schema validation rejects remote refs and nonfinite JSON. Independent
  sandbox egress/network restrictions, signed Registry manifests and credential
  vault integrations are NOT implemented here.
- `RuntimeResult.COMPLETED` is **not** independent Evaluation PASS.
  No hidden holdout, customer acceptance, quality gate or AgentStore release
  authority is included in agent 04.

## Owner / integrator blockers

1. **ADR-0002 owner-ratified GitHub approval**, including microservice boundaries,
   communication, data ownership and A2A transport auth.
2. Install/pin official SDK versions and run real LangGraph with PostgreSQL
   checkpoint persistence, real A2A independent client/server and fault tests.
3. Run Postgres effect ledger test and implement upstream external idempotency,
   reconcilers and transactional outbox at an owner-approved boundary.
4. Approve scoped Registry/MCP transport and signed manifests; add real egress
   sandbox, authentication, isolated credentials and observable audit events.
5. Provision mock-backed LiteLLM Proxy (dedicated PostgreSQL, hard budget
   enforcement) and independently verify model/provider routing.
6. Pass Ruff/Pyright and full dependency/security CI, independent evaluation,
   bilateral contract compatibility, owner security review and release approval.

### Rollback

Revert/disable candidate feature branch. No production traffic, schema migrations,
external A2A exposure, live orders/payments or actual customer data exist.
No merges performed by this workstream.

## 2026-10-27 security/consistency regression addendum

- AgentSpec version now hashes the **full frozen TaskSnapshot** (including its
  objective, budget, scopes, effects and policy), plus approved model, Registry
  revision and actual pinned tools. A changed objective cannot reuse the old
  AgentSpec version just because an external snapshot digest remains unchanged.
- Hashes canonicalize unordered set/frozenset inputs. Separate real Python
  subprocesses with three distinct `PYTHONHASHSEED` values produce identical
  AgentSpec versions/digests.
- Builder rejects tools that omit side-effect declarations. Tool identifiers are
  syntactically bounded (safe for inclusion as serialized prompt data).
- Tool arguments are recursively scanned for nested credential fields,
  unrepresentable JSON, deep structures and oversized UTF-8 payloads **before**
  any effect reservation or external call; alias `X-API-Key` is forbidden.
- The LiteLLM request now includes an explicit, JSON-defined ReAct decision
  contract and the complete pinned allowed tool-ID list. The provider still
  cannot authorize arbitrary tools: Gateway validates the returned action.
- Independent local test: `88 passed, 4 skipped` (Python 3.13).
  Coverage via `pytest --cov` is **82% overall**, Agent Builder core 94%,
  Runtime core 95%; LangGraph/official A2A/Postgres adapters need real SDK/DB
  integration. Compilation passes.
- SDK smoke tests and Ruff/Pyright are **NOT accepted** without executing the
  strict integration script successfully on the exact PR commit.

- A2A request authorization also verifies the released AgentSpec's digest against
  its actual immutable content on every request. A tampered prompt is rejected
  even when an earlier artifact digest is still allowlisted (regression-tested).

## 2026-10-27 hardening pass, isolated component tests

- Local Python 3.13 test suite: **88 passed, 4 skipped**, 82% coverage
  (Agent Builder core 94%, Runtime core 95%).
- `VerifiedToolGateway` limits UTF-8 output payloads to 32 KiB and refuses
  recursive/non-JSON structures before confirming an effect reservation.
- `postgres_checkpointer()` refuses to initialize unless
  `LANGGRAPH_STRICT_MSGPACK=true`; integration script sets it explicitly,
  following current official checkpoint deserialization guidance.
- Experimental A2A SDK adapter now requires `principal_scope` to stop
  cross-principal tasks/get exposure from a shared in-memory task store.
  Multi-principal production TaskStore requires a separately reviewed,
  authenticated per-principal durable storage implementation.
- Synthetic in-memory effect ledger now rejects confirmations without
  UNCERTAIN reservations or duplicate confirmation transitions.
- Builder JSON-quotes the task objective within policy instructions so raw
  task content cannot inject extra system-prompt lines.
- PostgreSQL effect ledger pre-validates result JSON (no NaN/Infinity,
  recursion, or oversized records) before acquiring a driver/connection.
- Reproducible strict integration gate without optional dependencies:
  4 skipped, **exit status 1** as expected (not accepted).
- Full Ruff/Pyright, real SDK and PostgreSQL tests are **not executed/passed**;
  actual production acceptance remains blocked on owner ADR-0002.

### Independent checks

```shell
python -m pytest -q tests/agent-engine -ra
python -m pytest -q tests/agent-engine --cov=agent_builder --cov=agent_runtime --cov=litellm_adapter --cov-report=term
AGENT_ENGINE_REQUIRE_INTEGRATIONS=1 python -m pytest -q tests/agent-engine/test_official_integrations.py tests/agent-engine/test_postgres_effects.py
```

## Scenario study and newly discovered defect (2026-10-27)

- Added `tests/agent-engine/SCENARIO_MATRIX.md` with 22 B2B scenarios,
  each tied to existing OpenSpec requirements, observable acceptance evidence,
  business risks and next gate.
- Added candidate bilateral buyer/supplier contract tests in
  `tests/agent-engine/test_bilateral_business_scenarios.py`: independently
  pinned specs, least-privilege tools, cross-tenant denial, partial build
  failure and live-payment denial. **These are not wire-level A2A tests**.
- The Railway test-gate deployment at **old commit `0cd81ba`** exposed a
  genuine **SyntaxError in `agent_builder/core.py` at line 62**. Earlier
  mock-test figures therefore cannot establish that commit's correctness.
  The malformed/duplicated source was repaired in commit `569a61f`;
  the real rebuild of that repair remains **NOT RUN**.
- Added `test_source_integrity.py` to parse every agent-04 Python module
  and reject duplicate classes in Builder. This regression is not a
  replacement for executable CI on the actual code revision.
- The local test fixture for two organizations is NOT equivalent to two
  independent official A2A SDK endpoints with conversation, Artifact and
  authenticated TaskStore state. No production release is authorized.

Status discipline: until a complete build runs on the **current SHA**, do
not repeat earlier test counts as acceptance evidence on this SHA.
