# A04: Agent catalogue, Mission Control, workflow progress and recovery

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A04; **ID:** STU-T06. **Requirements:** AF-REQ-105, 110, 111. **Test targets:** CJM-E2E-001, 008, 021, 022.

## Exclusive write allowlist
- apps/studio/src/features/agents/**
- apps/studio/src/features/workflows/**
- apps/studio/app/[locale]/w/[workspaceId]/agents/page.tsx
- apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/overview/**
- apps/studio/app/[locale]/w/[workspaceId]/workflows/**

## Shared constraints

- Start from integrator-provided C0 BASE_SHA. Branch from that exact revision and open a Draft PR; no direct main merge.
- Read docs/frontend/parallel/README.md; writes ONLY exclusive paths. Do not touch shared package manifests, route layouts/nav, generated source contracts, Java/Python services, docs/parallel/CONTRACTS_V0.md or ADR-0002.
- Call only typed Studio BFF exports. Treat source-authored status, tenant authorization and release/effect proofs as truth. No mock values on production screens.
- All pages: loading/empty/forbidden/unavailable/stale/partial/error; RU/EN keys, keyboard and ARIA semantics, SCSS Modules + theme tokens, responsive states.
- Every mutation follows allowedActions, CSRF/session, stable idempotency/expected revision, 401/403/409/429/503 recovery; frontend flag is no security authority.
- Unit/feature tests colocalized; document real outputs, SHA, skipped checks and missing service dependencies. Never claim full E2E or production readiness.

## Deliverables

1. Implement paginated/cursor-filterable Agent list, search, owner/status/environment controls, draft resume, last verified outcome and source staleness; no synthetic KPI placeholder as live.
2. Implement Agent Mission Control overview and links to other feature-owned tabs via integrator-published route registry; display independent quality and released version separately.
3. Build authoritative workflow state timeline with distinct Intake/Permissions/Build/Test/Evaluation/Repair/Release stages and server event timestamps. Show skipped vs blocked correctly; display source-specific required action.
4. Expandable operator-only stage details with correlation, operation receipt, tool selection and trace refs, sanitized; avoid cross-tenant secret leak.
5. Progress polling, offline/reconnect, timeouts/unknown statuses, idempotent build and retry only with valid server command capability.

## Definition of Done (local)

1. Real workflow revision always wins over late poll/older event; unknown state cannot show green terminal.
2. Duplicated build start uses same key; sandbox status never appears as released.
3. Agent list pagination and direct URL authorization checked; 403 vs source-down responses safe.
4. Component tests cover DRAFT, READY, BUILDING, TESTING, OPTIMIZING, VERIFIED, BLOCKED, RELEASED, ROLLED_BACK.

## Dependencies and blockers

A01 typed CP view/action ports, A02 Status/Timeline; I00 owns global nav and shared layouts.

## Suggested execution

1. Define feature's exported view/components/hook props in its own public entry; align to frozen Studio DTOs.
2. Build source-neutral UI including empty/forbidden/stale/partial/error before integrating live BFF.
3. Use synthetic fixtures with explicit DEMO markers in colocated tests only; never put fake values into production widgets.
4. Add negative state tests and style/accessibility checks. Do NOT add/edit global route layout or navigation.
5. Produce PR with allowed diff, test command+actual output, SHA, known blockers and a concise integration handoff for I00.

**Cross-agent change request:** use a feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct edit to other agents' files.
