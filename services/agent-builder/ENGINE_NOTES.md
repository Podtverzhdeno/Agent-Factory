# Agent Engine 04 — implementation and acceptance evidence

**Status:** ISOLATED COMPONENT IMPLEMENTATION. **Do not merge/release** until
owner ADR-0002 and independent integration/quality gates are satisfied.
**Branch:** `agent/04-agent-engine`; **target:** `docs/sdd-foundation-mvp`.
No shared OpenSpec, ADR, other agents' directories or production infrastructure changed.

## Requirement → tests

| Requirement | Candidate implementation | Evidence |
| --- | --- | --- |
| AF-REQ-005/006/029 | READY snapshot + BuildCommand, immutable versioned AgentSpec, deterministic minimum approved coverage, least-risk/grants tie-break, tenant-scoped idempotent BuildHandler | `test_build_handler.py`, `test_engine.py` |
| AF-REQ-007/016 | bounded ReAct candidate runtime, two different synthetic tasks, real generated RFQ XLSX and read-only supplier check | `test_engine.py`, `test_synthetic_demo.py`, `test_limits.py` |
| AF-REQ-012 | SQLite synthetic durable effect reservations, replay conflict and process-kill test; optional PostgreSQL transactional reservation + test | `test_durable_security.py`, `test_process_restart.py`, `test_postgres_effects.py` |
| AF-REQ-013 | authenticated ASGI/A2A boundary with dynamic release-revocation check; official SDK v1 route/client test (optional) | `test_a2a_security.py`, `test_official_integrations.py` |
| AF-REQ-023 | LiteLLM-compatible allowlisted model adapter; proxy-side token injection, authoritative cost header, max-output limit, model timeout | `test_litellm.py`, `test_limits.py` |
| AF-REQ-039/040/042/043 | LangGraph graph adapter, tenant/version-scoped checkpoint identity, SQLite thread/long-term TTL memory, optional AsyncPostgresSaver reopened-connection test | `test_langgraph_boundary.py`, `test_official_integrations.py`, `test_durable_security.py` |

## Actual local evidence (Python 3.13)

- `python -m pytest -q tests/agent-engine -ra`: **55 passed, 4 skipped**.
- `python -m compileall -q services tests`: completed.
- `pytest --cov=agent_builder --cov=agent_runtime --cov=litellm_adapter`:
  ~80% aggregate coverage, mostly optional integrations absent.
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
  release snapshots; full SDK conformance is **not verified**.
- MCP calls use explicit injected read-only transport and verified schema/scopes;
  remote MCP never grants authority and cannot dispatch consequential writes.
- LiteLLM HTTP adapter reads `x-litellm-response-cost` or mock `usage.cost`.
  Production quota requires centralized LiteLLM Proxy with database-backed
  spend controls, configured by integration owner; local response accounting is
  not a hard dollar ceiling before provider execution.

## Side-effect, privacy and security limitations

- Persist external effect reservation BEFORE executing a draft; an ambiguous
  outcome remains UNCERTAIN, and replay is DENIED pending reconciliation.
  SQLite tests demonstrate a real process termination. A PostgreSQL candidate
  ledger is provided but not run against a real database.
- No exactly-once guarantee: external tools must honor durable idempotency keys,
  and reconciliation/outbox must be implemented at the approved boundary.
- SQLite checkpoints/memory/run store are isolated plaintext synthetic fixtures:
  tenant/agent/thread isolation, bounded context and TTL covered by tests.
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
