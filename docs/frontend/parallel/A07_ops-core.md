# A07: Operator Console modules 1–5: Fleet, Workflows/Queues, Builder, Runtime, Registry

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A07. **Task:** STU-T09. **Requirements:** AF-REQ-112, 113, 121. **E2E targets:** CJM-E2E-012, 020, 021, 022.

## Exclusive write paths
- apps/studio/src/features/ops/core/**
- apps/studio/app/[locale]/ops/fleet/**
- apps/studio/app/[locale]/ops/workflows/**
- apps/studio/app/[locale]/ops/builder/**
- apps/studio/app/[locale]/ops/runtime/**
- apps/studio/app/[locale]/ops/registry/**

## Shared constraints

- Start from I00's single frozen C0 SHA. One branch/PR per agent; no direct merge to main or unapproved ADR decisions.
- Exclusive write paths ONLY; no shared root package/lockfile/Next layouts/central nav, OpenSpec global files, service OpenAPI or Java/Python code. Every other path is integrator or backend-owner property.
- Import public typed @studio/api/contracts/ui/charts/auth exports from C0. Mocks are explicitly DEMO-only in local tests; real capability must be evidence-backed and authorized.
- Screens include loading, empty, forbidden, degraded/stale, partial and error; RU/EN and keyboard/a11y; SCSS Modules and shared tokens.
- Unit/component tests and E2E coverage IDs with actual run logs/commit SHA; only I00 can claim integrated E2E on a common SHA.
- For missing shared type/API/UI component/dependency, create a request inside your own folder; never edit another feature's implementation.

## Deliverables

1. Fleet: actual deployment registry, health, versions, region/resource, readiness, last verification and incident deep links; no invented uptime. Limit secrets and resource names by auth.
2. Workflows & Queues: Orchestrator jobs, transitions, command outbox/inbox/DLQ if deployed, idempotency, safe retry, stuck-workflow investigation with source timestamps; differentiate lack of Kafka source from zero lag.
3. Builder & AgentSpecs: build status, immutable spec digests, tool version/reasons, prompt/harness diff access controlled, root cause of invalid build; no raw secret or hidden gold.
4. Runtime & Checkpoints: pinned tenant agent version, run, checkpoint/restart, effect evidence, memory boundary and safe deep links to run inspector; no false durable exactly-once guarantee.
5. Tool/MCP Registry: manifest lifecycle, scopes/version, maker-checker approval, revocation impact and capability denial reasons; only actual backend-ratified approvals callable.
6. Provide per-module source status and operator-only details with searchable/filterable paginated tables, charts via shared kit only when real aggregated series exist.

## Local acceptance / must test

1. All five routes usable with documented source-backed or explicit NOT_CONNECTED variants; correct operator permission and tenant scope.
2. Default operator has no implicit revoke/retry/release; denied mutation 403 captured as an auditable refusal.
3. Fleet and queue unavailable do not return 0 health issues or fake success; real source-as-of visible.
4. Feature-local tests for 5 module states; I00 integrates role gating and deep links.

## Blocking dependencies / collaboration handoff

A01 privileged BFF ops adapter, A02 chart/status/table primitives. Underlying live Kafka/registry/deploy health may be incomplete; no anonymous direct admin endpoints.

### Implementation order

1. Write feature-local exported component/action interfaces from frozen contracts; do not add root deps without I00 request.
2. Implement source-safe empty/forbidden/unsupported + synthetic fixture variants first.
3. Add intended UI interactions and local typed mocked transport; exercise happy and negative cases.
4. Log any unavailable upstream source as a BLOCKER; never promote unsupported user actions as operational.
5. Submit Draft PR with only owned diff, actual typecheck/lint/unit test outputs, SHA and integration handoff (API/error/state). No global E2E claim.

**Change protocol:** submit feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct change to another owner module, backend or shared contract.
