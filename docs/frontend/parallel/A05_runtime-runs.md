# A05: Sandbox Playground and verifiable Run Inspector

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A05; **ID:** STU-T07. **Requirements:** AF-REQ-106, 110, 123. **Test targets:** CJM-E2E-002, 004, 016, 020, 022.

## Exclusive write allowlist
- apps/studio/src/features/runs/**
- apps/studio/src/features/playground/**
- apps/studio/app/[locale]/w/[workspaceId]/runs/**
- apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/playground/**

## Shared constraints

- Start from integrator-provided C0 BASE_SHA. Branch from that exact revision and open a Draft PR; no direct main merge.
- Read docs/frontend/parallel/README.md; writes ONLY exclusive paths. Do not touch shared package manifests, route layouts/nav, generated source contracts, Java/Python services, docs/parallel/CONTRACTS_V0.md or ADR-0002.
- Call only typed Studio BFF exports. Treat source-authored status, tenant authorization and release/effect proofs as truth. No mock values on production screens.
- All pages: loading/empty/forbidden/unavailable/stale/partial/error; RU/EN keys, keyboard and ARIA semantics, SCSS Modules + theme tokens, responsive states.
- Every mutation follows allowedActions, CSRF/session, stable idempotency/expected revision, 401/403/409/429/503 recovery; frontend flag is no security authority.
- Unit/feature tests colocalized; document real outputs, SHA, skipped checks and missing service dependencies. Never claim full E2E or production readiness.

## Deliverables

1. Implement input request forms constrained by AgentSpec input schema and environment; sandbox clearly marked. File inputs use approved artifact refs, not local credential injection.
2. Run details show output artifact link, structured result, source run status, step spans, authenticated tool/policy decision, model route, cost when actually recorded, trace link and checkpoint/recovery state.
3. Effect evidence labels explicitly differentiate NONE/RESERVED/UNCONFIRMED/CONFIRMED_BY_EXTERNAL_RECEIPT/RECONCILIATION_REQUIRED; no 'payment complete' based on LLM text or effect_key.
4. Paginate and lazily expand large run timeline; multiple runs, refresh and concurrent run IDs remain stable; expensive waterfall should use shared chart kit only when real data.
5. Implement accessible output/file preview with short-lived authorization; safe download failure and expiry recovery; never cache hidden or another tenant's file.

## Definition of Done (local)

1. Missing external receipt scenario never shows business success; unsafe retry disabled without server reconciliation.
2. Large-span trace and list view remain bounded with lazy loading; no 100k-rows browser raw data.
3. Sandbox vs prod and source unavailable states accurate, file URL reauthorization on each access.
4. Unit tests for process kill/restart status projection and denied tools (mock source) do not claim real Runtime durability.

## Dependencies and blockers

A01 Runtime and Artifact BFF typed adapters, A02 UI/ChartKit; current real external receipt proof is missing for many business effects.

## Suggested execution

1. Define feature's exported view/components/hook props in its own public entry; align to frozen Studio DTOs.
2. Build source-neutral UI including empty/forbidden/stale/partial/error before integrating live BFF.
3. Use synthetic fixtures with explicit DEMO markers in colocated tests only; never put fake values into production widgets.
4. Add negative state tests and style/accessibility checks. Do NOT add/edit global route layout or navigation.
5. Produce PR with allowed diff, test command+actual output, SHA, known blockers and a concise integration handoff for I00.

**Cross-agent change request:** use a feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct edit to other agents' files.

## Mandatory live claim and activity trail — STU-T07

- Your live task record: [GitHub Issue #12](https://github.com/Podtverzhdeno/Agent-Factory/issues/12). Workstream assignment in this packet is **NOT a claim**; current issue starts BACKLOG/WAITING_FOR_C0 with no owner or time.
- Before work: consult [TASK_LEASE_PROTOCOL.md](TASK_LEASE_PROTOCOL.md); wait for trusted coordinator GRANTED with `lease_generation`, GitHub actor, UTC `claimed_at`, branch and BASE_SHA. If C0 or coordinator unavailable, do not claim it as active.
- During work: heartbeat at least every 20min; log meaningful progress with commit/PR/CI/test evidence and next action. Heartbeat and progress timestamps are separate; all event times are server-issued UTC.
- If no substantive progress for >120min: mark as stale candidate. A free compatible task takes precedence; with none, only the authorized coordinator after repo/PR/CI checks, owner notice and grace can grant a generation-fenced takeover. Old generation cannot complete the task.
- If taking over a prior task, record original owner/status/times/PR evidence and exact remaining work in Issue. Request integrator to add the handoff to OpenSpec, without editing shared tasks.md yourself; only the new approved generation can use delegated task-specific paths.
- An Issue assignment or label by itself is not a lock; automated coordinator and CI enforcement are still OPEN until STU-T19..23 pass actual tests.
