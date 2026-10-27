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
