# Railway Agent 04 integration gate (isolated staging candidate)

This is a **test appliance**, not the factory's production Agent Runtime.
It exposes only `/healthz` and `/readyz` after **every** integration
test and Ruff/Pyright check has succeeded. Neither endpoint performs agent
invocations or accepts customer data; both explicitly report
`production_ready: false`. Never assign a public domain to this service.

## Railway project

- Project: `ed32802c-7f84-47c3-b744-45e1fe2e6236`
- Current Railway production service `Agent-Factory` follows `main`.
  On 2026-10-27 it failed before compilation: only `README.md`
  was found in `main` and Railpack had no language marker or start script.
- Do **not** switch the existing production service to this test branch.
  Production service topology is gated on ADR-0002 owner ratification.

## Container contract

Build context: repository root, Dockerfile:
`tests/agent-engine/Dockerfile.railway-gate`.
Source branch: `agent/04-agent-engine` (or an immutable reviewed commit).
No app credentials, public domain, side-effectful production tools or customer
data. Before becoming healthy, entrypoint runs
`tests/agent-engine/run_integration_gates.sh`:
compileall → Ruff → Pyright → pytest
(`AGENT_ENGINE_REQUIRE_INTEGRATIONS=1` causes **any skip to fail**).

### Variables

- `AGENT_ENGINE_TEST_PG_DSN` must be a dedicated, disposable test database
  connection, not any live factory/other team's `DATABASE_URL`.
  Prefer Railway private networking.
- `LANGGRAPH_STRICT_MSGPACK=true`; the entrypoint sets this itself.
- `PORT` is provided by Railway.
- Never pass API keys, customer identifiers, real financial tasks or partner
  organization data into this gate.

### Acceptance criteria

1. Dedicated PostgreSQL test database exists, with separate credentials
   and no production data.
2. All SDK dependencies install from verified sources and actual integration
   tests execute without skips; mismatches are fixed on this feature branch.
3. Ruff and Pyright pass without silencing errors.
4. Deployment reaches terminal SUCCESS and private `/readyz` returns
   `all-required-checks-passed` only after gate succeeds.
5. Candidate remains **unreleased**; production deploy requires independent
   review plus owner-approved ADR-0002.

Rollback: remove test-only service and its **disposable test DB** after verifying
they contain no production data; leave the existing Agent-Factory service
unchanged. Database cleanup requires explicit data owner confirmation.

## Shared PostgreSQL protection / Free plan resource cap (2026-10-27)

The existing project's `Postgres.DATABASE_URL` belongs to the shared,
working database. **Do not use it for Agent 04 integration tests**.
The integration gate now validates host/user/database identity before any
DB-touching pytest: only a dedicated
`agent04-test-postgres.railway.internal` / `agent04_test` / `agent04_test`
DSN is accepted; no credentials are printed. Ruff and Pyright may run
without a DB first; both retain failure exit status.

Attempting to stage a separate PostgreSQL service in this project returned
`Free plan resource provision limit exceeded`. Nothing was provisioned.
Until capacity is available, production DB tests remain **BLOCKED**, never
redirected to the shared service. Do not mark a component as accepted.

## Safe pre-DB test phase

The integration gate now runs the entire Python test suite with all PostgreSQL
DSN and libpq environment variables explicitly **removed from that pytest
process**. This permits LangGraph in-memory and official A2A SDK tests to
execute even when a disposable PostgreSQL service cannot be provisioned.
Passing this first phase does not count as full integration acceptance; any
PostgreSQL skips are independently blocked by the strict phase, whose DSN
identity validator refuses the shared database.

## Latest measured gate (2026-10-27)

Agent Engine feature revision `b6d7c526`:
- Ruff **0**, Pyright **0**.
- Credential-free complete pytest run **144 passed, 2 skipped**.
- Official SDK client/server smoke plus **two-organization isolation** passed.
- Dedicated PostgreSQL gate intentionally **FAILED** with
  `TEST_DATABASE_NOT_ISOLATED`: Railway shared database variables
  are not a substitute for an isolated test resource.
- Consequently Railway deployment health is not SUCCESS and this is not a
  deployable business API.

When disposable isolated PostgreSQL capacity becomes available, change the
test service's `AGENT_ENGINE_TEST_PG_DSN` only to the verified isolated
`agent04-test-postgres` credentials; then repeat the exact strict gate
with no skips. No production database credentials should be copied.

## Strict pass using a disposable in-container PostgreSQL (2026-10-27)

The Agent 04 test appliance no longer needs an additional Railway
PostgreSQL service: its **test-only Dockerfile** installs PostgreSQL
and its entrypoint starts an ephemeral local cluster as the unprivileged
`postgres` OS user, listens on `127.0.0.1:55432`, creates
`agent04_test` owned by `agent04_test`, and overrides all Railway
shared-DB variables **before** any database access. Tests first run
without any DB credentials, and then rerun strictly against the
validated ephemeral DSN. On failure, the cluster is stopped and health
is unavailable; on success, it stops before the health endpoint starts.

**Proven result:** Railway deployment `c6b50c6f-72d5-41e6-b6d2-fd8a662514b0`
at commit `295f3fab` reached **SUCCESS**:
Ruff 0, Pyright 0, **148 passed / 0 skipped** in strict mode.
No extra Railway database or persistent volume was purchased.
The existing shared `Postgres` remains untouched.

This is an isolated technical CI appliance, **not** a production
PostgreSQL topology or a substitute for external A2A/MCP/business E2E
or owner-approved ADR-0002. The probe sets `production_ready=false`.
