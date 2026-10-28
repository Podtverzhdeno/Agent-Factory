# A10: Two-company A2A collaborative creation, invitations, private evaluation and cross-play

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A10. **Task:** STU-T12. **Requirements:** AF-REQ-116, 117, 118, 121. **E2E targets:** CJM-E2E-014, 015, 017, 018.

## Exclusive write paths
- apps/studio/src/features/bilateral/**
- apps/studio/app/[locale]/w/[workspaceId]/scenarios/**

## Shared constraints

- Start from I00's single frozen C0 SHA. One branch/PR per agent; no direct merge to main or unapproved ADR decisions.
- Exclusive write paths ONLY; no shared root package/lockfile/Next layouts/central nav, OpenSpec global files, service OpenAPI or Java/Python code. Every other path is integrator or backend-owner property.
- Import public typed @studio/api/contracts/ui/charts/auth exports from C0. Mocks are explicitly DEMO-only in local tests; real capability must be evidence-backed and authorized.
- Screens include loading, empty, forbidden, degraded/stale, partial and error; RU/EN and keyboard/a11y; SCSS Modules and shared tokens.
- Unit/component tests and E2E coverage IDs with actual run logs/commit SHA; only I00 can claim integrated E2E on a common SHA.
- For missing shared type/API/UI component/dependency, create a request inside your own folder; never edit another feature's implementation.

## Deliverables

1. Implement advanced mode selection and scenario onboarding: invite Company B with expiring grant, both companies consent and establish exact disclosed A2A interface, budget, schema, data sharing.
2. Display two independent BTP/version cards (A and B), separate approved tool grants and build state; client A never sees B's private files, prompt, memory, source data or signed evaluation gold.
3. Design A/B three-column UI (A lane / permitted A2A exchange / B lane), with disclosure labels and distinct private vs shared evidence views. Demo-preview only until actual bilateral IAM service works.
4. Render per-party Evaluation A and B plus independently authorized joint outcome, cross-play matrix A0×B0 / A1×B0 / A0×B1 / A1×B1, immutable digests and distinct approval gates.
5. Handle partner offline, consent revoked, API mismatch, unavailable A2A service, cancelled invite, stale agent version, privacy and separate release rollback. No unilateral auto-optimization of partner's agent.
6. Provide safe links into existing A03 task wizard and A06 quality/versions through route contracts (no internal imports from those features).

## Local acceptance / must test

1. B consent required before shared build/eval; denied or revoked consent blocks next actions and redacts subsequent data.
2. Mutations to B's BTP/AgentSpec/release from A role impossible via UI and server; false joint PASS cannot override individual veto.
3. Cross-play results tied to frozen counterpart versions and separate baseline; no private traces shown to other party.
4. Mode clearly EXPERIMENTAL/DISABLED until backend two-tenant E2E and real A2A consent verified; component previews are not labelled live.

## Blocking dependencies / collaboration handoff

A01 BFF bilateral API/tenant-consent adapters (probably proposed only), A02 UI/chart, I00 route integration. Underlying bilateral Orchestrator/Evaluation/consent/invitation endpoints currently only RFC.

### Implementation order

1. Write feature-local exported component/action interfaces from frozen contracts; do not add root deps without I00 request.
2. Implement source-safe empty/forbidden/unsupported + synthetic fixture variants first.
3. Add intended UI interactions and local typed mocked transport; exercise happy and negative cases.
4. Log any unavailable upstream source as a BLOCKER; never promote unsupported user actions as operational.
5. Submit Draft PR with only owned diff, actual typecheck/lint/unit test outputs, SHA and integration handoff (API/error/state). No global E2E claim.

**Change protocol:** submit feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct change to another owner module, backend or shared contract.

## Mandatory live claim and activity trail — STU-T12

- Your live task record: [GitHub Issue #17](https://github.com/Podtverzhdeno/Agent-Factory/issues/17). Workstream assignment in this packet is **NOT a claim**; current issue starts BACKLOG/WAITING_FOR_C0 with no owner or time.
- Before work: consult [TASK_LEASE_PROTOCOL.md](TASK_LEASE_PROTOCOL.md); wait for trusted coordinator GRANTED with `lease_generation`, GitHub actor, UTC `claimed_at`, branch and BASE_SHA. If C0 or coordinator unavailable, do not claim it as active.
- During work: heartbeat at least every 20min; log meaningful progress with commit/PR/CI/test evidence and next action. Heartbeat and progress timestamps are separate; all event times are server-issued UTC.
- If no substantive progress for >120min: mark as stale candidate. A free compatible task takes precedence; with none, only the authorized coordinator after repo/PR/CI checks, owner notice and grace can grant a generation-fenced takeover. Old generation cannot complete the task.
- If taking over a prior task, record original owner/status/times/PR evidence and exact remaining work in Issue. Request integrator to add the handoff to OpenSpec, without editing shared tasks.md yourself; only the new approved generation can use delegated task-specific paths.
- An Issue assignment or label by itself is not a lock; automated coordinator and CI enforcement are still OPEN until STU-T19..23 pass actual tests.
