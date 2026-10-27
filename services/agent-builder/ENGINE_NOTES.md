# Agent Engine — proposed isolated component (ADR-0002 pending)

This work packet implements testable mock-backed components, **not** approved deployable topology.
Shared `openspec/**`, `docs/parallel/**` and architecture ADRs are deliberately untouched.

## Requirement → executable component test

| AF-REQ | Component | Tests |
|---|---|---|
| 005/006/029 | immutable versioned spec, minimal authorized set cover | minimum-set test; denied tools/grants |
| 007/016 | two distinct task packages, bounded runtime | two-task test; tenant, steps, budget, tamper |
| 012 | no repeat after uncertain external effect | crash/replay denial |
| 013 | A2A release + caller permission boundary | A2A unauthorized test |
| 023 | LiteLLM route, server-side secret injection and authoritative usage | proxy tests |

## Local verification

Run `python -m pytest -q tests/agent-engine` after installing dependencies in
`tests/agent-engine/requirements.txt`. The synthetic tests require NO other factory service.

## Architecture / security limitations

- `authorized_scopes` is an externally granted fixture value; Builder cannot authorize permissions.
- The immutable AgentSpec contains only synthetic objective text; real prompts and private artifacts
  need tenant-scoped encrypted storage. Digest is an integrity check, **not a signature**.
- `Runtime.run` is an in-process candidate component. `langgraph_adapter.build_graph`
  produces the real decide→tool→decide StateGraph only when `langgraph` is installed.
  The Postgres saver factory exists, but a real Postgres restart test is **not verified**.
- `EffectLedger` is **in-memory mock**. Once an ambiguous side effect is reserved, the same
  key is blocked even after a logical runtime restart *sharing that mock*. Process termination
  requires durable transaction/ledger and external reconciliation; **no exactly-once claim**.
- `A2ABoundary` is **only identity and release checking**. Official A2A SDK HTTP server,
  conformance tests and separate-client invocation are **BLOCKED**, not simulated with
  a homegrown wire protocol. Unreleased candidates must never be externally callable.
- LiteLLM adapter calls a fake OpenAI-compatible proxy; shared LiteLLM deployment, budgets,
  auth, cost accounting, failover and provider keys remain an integration-owner concern.
- Full registry input/output JSON Schema validation, verified MCP endpoints, credentials,
  production egress policy, trace sink and signed spec verification are NOT implemented.
  Reject these paths until corresponding owner-approved adapters exist.
- Owner must ratify microservice communication, storage ownership and deployment in ADR-0002
  before implementing service topology. This PR neither approves ADR nor claims system E2E.

## Threats and rollback

Threats: prompt/tool injection, tenant crossover, forged grants, privilege escalation, duplicate
external operations, forged model cost, leaked provider secrets, stale memory. Boundaries deny
unknown tools and consequential effects; all customer integrations are mocks.
Rollback: remove candidate from development build; no production routes or migrations changed.
