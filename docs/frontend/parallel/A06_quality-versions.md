# A06: Evaluation, GEPARD candidate/retest, AgentStore versions and controlled releases

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A06. **Task:** STU-T08. **Requirements:** AF-REQ-107, 108, 109, 121. **E2E targets:** CJM-E2E-003, 004, 009, 010, 011, 024.

## Exclusive write paths
- apps/studio/src/features/quality/**
- apps/studio/src/features/gepard/**
- apps/studio/src/features/versions/**
- apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/quality/**
- apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/versions/**
- apps/studio/app/[locale]/w/[workspaceId]/releases/**

## Shared constraints

- Start from I00's single frozen C0 SHA. One branch/PR per agent; no direct merge to main or unapproved ADR decisions.
- Exclusive write paths ONLY; no shared root package/lockfile/Next layouts/central nav, OpenSpec global files, service OpenAPI or Java/Python code. Every other path is integrator or backend-owner property.
- Import public typed @studio/api/contracts/ui/charts/auth exports from C0. Mocks are explicitly DEMO-only in local tests; real capability must be evidence-backed and authorized.
- Screens include loading, empty, forbidden, degraded/stale, partial and error; RU/EN and keyboard/a11y; SCSS Modules and shared tokens.
- Unit/component tests and E2E coverage IDs with actual run logs/commit SHA; only I00 can claim integrated E2E on a common SHA.
- For missing shared type/API/UI component/dependency, create a request inside your own folder; never edit another feature's implementation.

## Deliverables

1. Create independent Evaluation Scorecard with PASSED/FAILED/BLOCKED/INCONCLUSIVE/UNAVAILABLE, dataset/version, case count, signed evidence status, safety veto, tool-effect proof and per-case safe finding aggregates. Hidden holdout gold must NEVER enter UI or logs.
2. Implement baseline/candidate comparators: immutable AgentSpec IDs, quality, latency p95 and spend with verified denominator; quality regression/inconclusive must not be shown as improvement. Recharts/ECharts should go through A02 ChartKit public API.
3. Implement GEPARD experiment list, candidate diff and bounded optimization request. Real GEPA vs deterministic mock must be displayed honestly; no silent direct production prompt editing.
4. Implement Version/Release view: CANDIDATE, VERIFIED, RELEASED, ROLLED_BACK are distinct; pinned digests, approvals, release-target environment, independent quality and previous release rollback reference.
5. Release/rollback requires explicit user intent, server allowed action, reauthorization/approval, idempotency, confirmation and effect/reconciliation warnings. Never show optimistic release on a 202 request.
6. Implement no-evidence, signature failure, expired approval, unsupported status and eval service down states.

## Local acceptance / must test

1. No forged evaluation or unverified effect yields client PASS; sealed holdout correct answers never appear.
2. GEPARD candidate failing any hard gate cannot be labeled promoted or 'automatically improved'; mock backend clearly tagged.
3. Missing approval, stale version or broken deploy returns disabled/rejected release, no false release badge.
4. Keyboard accessible diff/quality and release dialogs; audit ref shown after confirmed command receipt.

## Blocking dependencies / collaboration handoff

A01 BFF evaluation/GEPARD/AgentStore/release ports, A02 UI and ChartKit. Actual GEPA and production release E2E remain backend blockers; user-facing live claims are disabled pending acceptance.

### Implementation order

1. Write feature-local exported component/action interfaces from frozen contracts; do not add root deps without I00 request.
2. Implement source-safe empty/forbidden/unsupported + synthetic fixture variants first.
3. Add intended UI interactions and local typed mocked transport; exercise happy and negative cases.
4. Log any unavailable upstream source as a BLOCKER; never promote unsupported user actions as operational.
5. Submit Draft PR with only owned diff, actual typecheck/lint/unit test outputs, SHA and integration handoff (API/error/state). No global E2E claim.

**Change protocol:** submit feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct change to another owner module, backend or shared contract.

## Mandatory live claim and activity trail — STU-T08

- Your live task record: [GitHub Issue #13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13). Workstream assignment in this packet is **NOT a claim**; current issue starts BACKLOG/WAITING_FOR_C0 with no owner or time.
- Before work: consult [TASK_LEASE_PROTOCOL.md](TASK_LEASE_PROTOCOL.md); wait for trusted coordinator GRANTED with `lease_generation`, GitHub actor, UTC `claimed_at`, branch and BASE_SHA. If C0 or coordinator unavailable, do not claim it as active.
- During work: heartbeat at least every 20min; log meaningful progress with commit/PR/CI/test evidence and next action. Heartbeat and progress timestamps are separate; all event times are server-issued UTC.
- If no substantive progress for >120min: mark as stale candidate. A free compatible task takes precedence; with none, only the authorized coordinator after repo/PR/CI checks, owner notice and grace can grant a generation-fenced takeover. Old generation cannot complete the task.
- If taking over a prior task, record original owner/status/times/PR evidence and exact remaining work in Issue. Request integrator to add the handoff to OpenSpec, without editing shared tasks.md yourself; only the new approved generation can use delegated task-specific paths.
- An Issue assignment or label by itself is not a lock; automated coordinator and CI enforcement are still OPEN until STU-T19..23 pass actual tests.
