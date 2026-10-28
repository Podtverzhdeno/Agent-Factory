# A01: Platform shell, OIDC, BFF and capability/read-model adapters

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A01; **ID:** STU-T03. **Requirements:** AF-REQ-100, 110, 121, 122, 124. **Test targets:** CJM-E2E-006, 008, 009, 018, 022; negative access matrix.

## Exclusive write allowlist
- apps/studio/src/server/**
- apps/studio/src/shared/api/**
- apps/studio/src/shared/auth/**
- apps/studio/src/shared/capabilities/**
- apps/studio/src/app-shell/**
- apps/studio/app/api/studio/**
- apps/studio/app/(auth)/**
- apps/studio/src/features/platform/**

## Shared constraints

- Start from integrator-provided C0 BASE_SHA. Branch from that exact revision and open a Draft PR; no direct main merge.
- Read docs/frontend/parallel/README.md; writes ONLY exclusive paths. Do not touch shared package manifests, route layouts/nav, generated source contracts, Java/Python services, docs/parallel/CONTRACTS_V0.md or ADR-0002.
- Call only typed Studio BFF exports. Treat source-authored status, tenant authorization and release/effect proofs as truth. No mock values on production screens.
- All pages: loading/empty/forbidden/unavailable/stale/partial/error; RU/EN keys, keyboard and ARIA semantics, SCSS Modules + theme tokens, responsive states.
- Every mutation follows allowedActions, CSRF/session, stable idempotency/expected revision, 401/403/409/429/503 recovery; frontend flag is no security authority.
- Unit/feature tests colocalized; document real outputs, SHA, skipped checks and missing service dependencies. Never claim full E2E or production readiness.

## Deliverables

1. Build server-side OIDC session and scoped workspace/environment resolver; user-visible shell role switches are backed by trusted grants; no raw bearer/keys in browser. Auth ownership must align with the integrator-approved IAM plan.
2. Expose typed client interfaces and BFF Route Handlers from frozen CJM_UI_CONTRACTS_AND_E2E.md for all feature agents; each endpoint is deny-by-default and uses source-owned auth/revision checks. Provider adapter returns UNAVAILABLE when upstream missing, not invented fixtures.
3. Handle 202 async receipt, Idempotency-Key, If-Match, safe error envelope, bounded timeouts, correlation logging, partial read model with source stamps and stable cache isolation by workspace and viewer.
4. Provide effective capabilities endpoint from real service readiness, entitlement, source evidence and user allowed actions. IDEA_ONLY graph editor/microfrontends are never unlocked by a static catalog.
5. Support active-page polling client with 3–5s visibility-aware interval, exponential backoff on overload and authoritative refetch on staleness; no required initial Redis/SSE dependency.
6. Provide server-only protected artifact access and strict privileged ops adapter registration, never arbitrary string command invocation or cross-tenant stream channels.

## Definition of Done (local)

1. Two-tenant auth tests on agent, run, chart, artifact, direct URL, workspace switch and negative role cases; no resource existence leak.
2. Unknown API enum or service 500 gives unsupported/degraded with no privileged mutation; no fake green data.
3. Double submit / timeout returns same operation ID, not duplicate Build/Release action; session tokens are never bundled.
4. Typecheck, lint and transport unit tests pass on pinned commit; any absent upstream is listed as blocker.

## Dependencies and blockers

Frozen DTOs, OIDC/CSRF selection and BFF route mapping from I00; source OpenAPI is versioned and cannot be changed here.

## Suggested execution

1. Define feature's exported view/components/hook props in its own public entry; align to frozen Studio DTOs.
2. Build source-neutral UI including empty/forbidden/stale/partial/error before integrating live BFF.
3. Use synthetic fixtures with explicit DEMO markers in colocated tests only; never put fake values into production widgets.
4. Add negative state tests and style/accessibility checks. Do NOT add/edit global route layout or navigation.
5. Produce PR with allowed diff, test command+actual output, SHA, known blockers and a concise integration handoff for I00.

**Cross-agent change request:** use a feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct edit to other agents' files.

## Mandatory live claim and activity trail — STU-T03

- Your live task record: [GitHub Issue #8](https://github.com/Podtverzhdeno/Agent-Factory/issues/8). Workstream assignment in this packet is **NOT a claim**; current issue starts BACKLOG/WAITING_FOR_C0 with no owner or time.
- Before work: consult [TASK_LEASE_PROTOCOL.md](TASK_LEASE_PROTOCOL.md); wait for trusted coordinator GRANTED with `lease_generation`, GitHub actor, UTC `claimed_at`, branch and BASE_SHA. If C0 or coordinator unavailable, do not claim it as active.
- During work: heartbeat at least every 20min; log meaningful progress with commit/PR/CI/test evidence and next action. Heartbeat and progress timestamps are separate; all event times are server-issued UTC.
- If no substantive progress for >120min: mark as stale candidate. A free compatible task takes precedence; with none, only the authorized coordinator after repo/PR/CI checks, owner notice and grace can grant a generation-fenced takeover. Old generation cannot complete the task.
- If taking over a prior task, record original owner/status/times/PR evidence and exact remaining work in Issue. Request integrator to add the handoff to OpenSpec, without editing shared tasks.md yourself; only the new approved generation can use delegated task-specific paths.
- An Issue assignment or label by itself is not a lock; automated coordinator and CI enforcement are still OPEN until STU-T19..23 pass actual tests.
