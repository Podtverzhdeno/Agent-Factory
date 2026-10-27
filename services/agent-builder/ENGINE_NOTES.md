# Agent Engine 04 — contract-first isolated candidate

**Owner architectural gate:** ADR-0002 not ratified. No production service topology,
external A2A exposure, live tool effects, release authority or partner data processing.

## Verifiable slice and run instructions

Python 3.12+ dependencies: `python -m pip install -r tests/agent-engine/requirements.txt`.
From the repository root, run `python -m pytest -q tests/agent-engine`.
Synthetic RFQ fixture is made by `agent_runtime.synthetic_demo.execute_two_tasks(work_dir)`:
one generated XLSX RFQ, approved catalog lookup and draft XLSX; second supplier
status read-only. Same Builder/Runtime source, distinct pinned AgentSpecs.

## Requirement → test evidence

| Requirements | Component | Tests |
|---|---|---|
| AF-REQ-005/006/029 | immutable AgentSpec, deterministic minimal approved coverage | test_engine.py |
| AF-REQ-007/016 | bounded runtime, two distinct configurations | test_engine.py, test_synthetic_demo.py |
| AF-REQ-012 | disk-backed effect reservation and simulated restart | test_durable_security.py |
| AF-REQ-013 | A2A authorization + release boundary (NOT official SDK) | test_engine.py |
| AF-REQ-023 | mock LiteLLM proxy model route/cost/error | test_litellm.py |
| AF-REQ-039/040/042/043 | threads/tenant scoped memory, tool pin/schema checks | test_durable_security.py |

## Security design

- All effects use explicit runtime grants, tenant+agent+tool-version+manifest
  digest and local input/output JSON Schemas. Unknown tools and schemas fail closed.
- The local `VerifiedToolGateway` requires trusted registry-provisioned `ToolPolicy`;
  it does **not** itself authenticate Registry. Reject all unverified gateways in Runtime.
- Tool schemas prohibit dynamic/remote `$ref`; no implicit MCP download/install.
- For a non-read external operation, a durable SQLite demo ledger writes a unique
  reservation **before** calling the fake tool. Unknown outcomes stay UNCERTAIN and
  are never retried automatically. This proves local replay denial, NOT exactly-once.
- SQLite memory is plaintext and **synthetic-only**; tenant/agent/thread keys and
  TTL prevent logical cross-tenant reads. Production encryption, ACL and retention
  policies require owner decisions.
- `model_route`, credentials, manifest digest and approval state are supplied
  by trusted external ports; no secret is embedded in AgentSpec or prompt.
- The run status `COMPLETED` means a candidate execution terminated normally.
  It does **not** mean business task VERIFIED or evaluation PASSED.

## Explicit BLOCKED work and remaining risks

1. ADR-0002 service boundaries, databases, communication, release authority,
   authenticated APIs and independent architecture approval.
2. Official A2A SDK v1 server/client conformance and authenticated calls. The
   current A2ABoundary is an authorization port only.
3. Real LangGraph execution with `AsyncPostgresSaver`, `setup()`, process-kill
   test and tenant-bound checkpoint ownership. Optional adapter is present but
   dependencies and Postgres are unavailable in current sandbox.
4. PostgreSQL transactional effect ledger/outbox + business-side external
   idempotency key reconciliation. SQLite adapter is **not** production.
5. Authenticated Registry grants, approved per-tool schema sourcing, real
   MCP transport, egress isolation and credentials (local tool timeout enforced).
6. True LiteLLM Proxy tenant quota/billing, model provenance and resilient
   failure handling. Tests use HTTP fake and no real provider.
7. Full CI (ruff, pyright, dependency/license scan), production threat review,
   HIL approvals, acceptance and end-to-end pilot evaluation.

## Operational notes

No production credentials or customer content. Local files contain only synthetic
test data. External source licenses: Pydantic MIT, LangGraph MIT (optional),
jsonschema MIT, HTTPX BSD-3-Clause, openpyxl MIT, pytest MIT.
Check actual pinned transitive licenses before release.

Rollback: revert this feature commit/disable candidate; no deployed services,
production migrations or released AgentStore versions are affected.
Never merge this work packet until owner/integrator acceptance and all critical gates.
