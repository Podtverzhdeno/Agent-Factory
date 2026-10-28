# A08: Operator Console modules 6–10: connectors, artifacts, evaluation, GEPARD, models

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A08. **Task:** STU-T10. **Requirements:** AF-REQ-112, 113, 114, 121. **E2E targets:** CJM-E2E-009, 012, 013, 019, 020.

## Exclusive write paths
- apps/studio/src/features/ops/pipelines/**
- apps/studio/app/[locale]/ops/connectors/**
- apps/studio/app/[locale]/ops/artifacts/**
- apps/studio/app/[locale]/ops/evaluation/**
- apps/studio/app/[locale]/ops/gepard/**
- apps/studio/app/[locale]/ops/models/**

## Shared constraints

- Start from I00's single frozen C0 SHA. One branch/PR per agent; no direct merge to main or unapproved ADR decisions.
- Exclusive write paths ONLY; no shared root package/lockfile/Next layouts/central nav, OpenSpec global files, service OpenAPI or Java/Python code. Every other path is integrator or backend-owner property.
- Import public typed @studio/api/contracts/ui/charts/auth exports from C0. Mocks are explicitly DEMO-only in local tests; real capability must be evidence-backed and authorized.
- Screens include loading, empty, forbidden, degraded/stale, partial and error; RU/EN and keyboard/a11y; SCSS Modules and shared tokens.
- Unit/component tests and E2E coverage IDs with actual run logs/commit SHA; only I00 can claim integrated E2E on a common SHA.
- For missing shared type/API/UI component/dependency, create a request inside your own folder; never edit another feature's implementation.

## Deliverables

1. Connectors & Secrets: list approved integrations, health, scopes, credential expiry/rotation status and safe consent requests without ever rendering raw secrets or provider keys.
2. Task Intake & Artifacts: ingestion jobs, failed/rejected documents, parser provenance, versioned BTP, retention/classification and safe links; not a broad customer-file download list.
3. Evaluation & Holdouts: signed evidence jobs, case counts/failure taxonomy, data partition status, vault readiness, job lease and parser effects; gold answers and sealed files hidden even from routine operator.
4. GEPARD Experiments: real vs mock optimizer distinction, candidate lineage, budgets, tuning/validation status, baseline/retest and blockers. Do not add training triggers to GEPARD.
5. Models & LiteLLM: provider health, model route, tokens, real usage, budget allowlist, uncertain pricing, fallback and failure. No invented amounts; label costs incomplete until reconciled.
6. Shared chart kit: 5 domain-approved charts such as model spend stacked bars, quality trends, error distributions, optimizer scatter and ingestion health, gated by real series.

## Local acceptance / must test

1. All five operator routes have correct no-data vs no-service states and explicit data provenance.
2. Secret request body, holdout gold and provider key never appear in HTML, logs or cache; wrong roles denied.
3. Cost with no trusted usage is UNKNOWN, not zero; mock optimizer never called real successful GEPA.
4. Feature tests include missing KMS, provider failure, intake not deployed and cross-tenant negative.

## Blocking dependencies / collaboration handoff

A01 scoped BFF Ops/eval/optimizer/provider adapters; A02 typed chart kit. Missing external KMS and LiteLLM persistent budgets must be reported as blockers.

### Implementation order

1. Write feature-local exported component/action interfaces from frozen contracts; do not add root deps without I00 request.
2. Implement source-safe empty/forbidden/unsupported + synthetic fixture variants first.
3. Add intended UI interactions and local typed mocked transport; exercise happy and negative cases.
4. Log any unavailable upstream source as a BLOCKER; never promote unsupported user actions as operational.
5. Submit Draft PR with only owned diff, actual typecheck/lint/unit test outputs, SHA and integration handoff (API/error/state). No global E2E claim.

**Change protocol:** submit feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct change to another owner module, backend or shared contract.

## Mandatory live claim and activity trail — STU-T10

- Your live task record: [GitHub Issue #15](https://github.com/Podtverzhdeno/Agent-Factory/issues/15). Workstream assignment in this packet is **NOT a claim**; current issue starts BACKLOG/WAITING_FOR_C0 with no owner or time.
- Before work: consult [TASK_LEASE_PROTOCOL.md](TASK_LEASE_PROTOCOL.md); wait for trusted coordinator GRANTED with `lease_generation`, GitHub actor, UTC `claimed_at`, branch and BASE_SHA. If C0 or coordinator unavailable, do not claim it as active.
- During work: heartbeat at least every 20min; log meaningful progress with commit/PR/CI/test evidence and next action. Heartbeat and progress timestamps are separate; all event times are server-issued UTC.
- If no substantive progress for >120min: mark as stale candidate. A free compatible task takes precedence; with none, only the authorized coordinator after repo/PR/CI checks, owner notice and grace can grant a generation-fenced takeover. Old generation cannot complete the task.
- If taking over a prior task, record original owner/status/times/PR evidence and exact remaining work in Issue. Request integrator to add the handoff to OpenSpec, without editing shared tasks.md yourself; only the new approved generation can use delegated task-specific paths.
- An Issue assignment or label by itself is not a lock; automated coordinator and CI enforcement are still OPEN until STU-T19..23 pass actual tests.
