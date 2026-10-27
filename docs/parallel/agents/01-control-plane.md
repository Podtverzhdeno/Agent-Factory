# AGENT 01 — Factory Control Plane + AgentStore

**Branch:** agent/01-control-plane
**You own only:** \`services/factory-orchestrator/**\`, \`services/agent-store/**\`, \`tests/control-plane/**\`
**Stack:** Java 21+, Spring Boot, PostgreSQL, REST/OpenAPI, Kafka adapters. AgentStore is a proposed ownership module; do NOT assert it must be an independent deployable before owner ADR ratification.
**Relevant requirements:** AF-REQ-001/002 (workflow command side), AF-REQ-010/011 (bounded retry control), AF-REQ-014/015, AF-REQ-021 (local tests), AF-REQ-030 (snapshot lifecycle consumer), AF-REQ-045/046, AF-REQ-048 (quality-gated route promotion).

## One independently owned task

Create a control-plane domain that **explicitly** starts Builder/Evaluation/GEPARD and direct optional Soup commands through mocked ports; tracks durable build/evaluation/repair/release states, decisions, budgets, approvals and tenant-scoped AgentStore versions. Kafka is notification/async completion, never a hidden planner. No other module implementation required to develop/test your state machine.

## Interfaces to implement using mocks initially

- \`TaskSnapshotReader\` (returns READY immutable snapshot from workstream 02).
- \`BuildClient\` with \`POST /internal/builds\` from CONTRACTS_V0; return accepted build ID.
- \`EvaluationClient\` and \`OptimizationClient\` (workstream 05).
- \`AgentStoreRepository\` for immutable versioned agent release records (workstream 01), plus \`ReleasePolicy\`.
- \`EventInbox\`, \`OutboxPublisher\`, \`Clock\`, \`TenantAuthz\`. Correlation/event IDs and idempotency keys mandatory.

## Concrete deliverables

1. Isolated domain state machine: DRAFT -> READY -> BUILDING -> TESTING -> OPTIMIZING -> RE_TESTING -> VERIFIED/BLOCKED -> RELEASED/ROLLED_BACK. Terminating max retries, spend/time guard and error taxonomy.
2. Ports and typed REST DTOs based on contracts v0; no implicit dependence on another team's actual service.
3. AgentStore candidate version records and promotion policy; cryptographically pinned artifact references; separate customer approval and rollback metadata.
4. Kafka event handling: deduplication/inbox, transactional outbox and stale/out-of-order event handling behind local adapters. Do not claim Kafka exactly-once external effects.
5. Unit/component tests for explicit build triggering, stop on safety veto, missing gold/holdout, version mismatch, budget exhausted, idempotent duplicate commands, unauthorized tenant, low-risk auto promotion only after complete evidence.
6. OpenAPI example, concise diagram, local tests and a PR with actual evidence. Do NOT modify shared OpenSpec or ADR.

## Acceptance

- Mock-backed workflow covers \`READY -> build -> eval fail -> GEPARD candidate -> eval pass -> gated release\`.
- Failing guard exits BLOCKED and does not publish to released channel.
- Events never begin a build without an authorized workflow command.
- It is possible to test all above while 02/03/04/05 have zero running deployments.

## Exclusions

No business-document extraction, tool catalogue, agent code, actual evaluation scores, GEPARD algorithm or Soup training; those belong elsewhere. No cross-service DB reads. No main merge.

## Copy/paste launch prompt

> Work exclusively on Agent Factory workstream **01 Control Plane** using branch **agent/01-control-plane**. Read \`AGENTS.md\`, \`docs/parallel/README.md\`, \`docs/parallel/CONTRACTS_V0.md\` and this file. Work ONLY in \`services/factory-orchestrator/**\`, \`services/agent-store/**\`, \`tests/control-plane/**\`. Build mock-backed typed Java state machine and release/AgentStore interfaces; prove exact acceptance tests and open a PR into \`docs/sdd-foundation-mvp\`. Do not edit shared specs/contracts or other services. Respect unapproved ADR-0002: no claims or implementation of ratified deployment topology; report it as BLOCKED if it prevents work.
