# A03: Create Agent wizard with BTP, files, approvals and integrations

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A03; **ID:** STU-T05. **Requirements:** AF-REQ-101..104, 123. **Test targets:** CJM-E2E-001, 005, 007, 023.

## Exclusive write allowlist
- apps/studio/src/features/task-intake/**
- apps/studio/app/[locale]/w/[workspaceId]/agents/new/**
- apps/studio/app/[locale]/w/[workspaceId]/tasks/**

## Shared constraints

- Start from integrator-provided C0 BASE_SHA. Branch from that exact revision and open a Draft PR; no direct main merge.
- Read docs/frontend/parallel/README.md; writes ONLY exclusive paths. Do not touch shared package manifests, route layouts/nav, generated source contracts, Java/Python services, docs/parallel/CONTRACTS_V0.md or ADR-0002.
- Call only typed Studio BFF exports. Treat source-authored status, tenant authorization and release/effect proofs as truth. No mock values on production screens.
- All pages: loading/empty/forbidden/unavailable/stale/partial/error; RU/EN keys, keyboard and ARIA semantics, SCSS Modules + theme tokens, responsive states.
- Every mutation follows allowedActions, CSRF/session, stable idempotency/expected revision, 401/403/409/429/503 recovery; frontend flag is no security authority.
- Unit/feature tests colocalized; document real outputs, SHA, skipped checks and missing service dependencies. Never claim full E2E or production readiness.

## Deliverables

1. Build resumable 3–5 step task wizard: business goal/process/trigger/output; files and example pairs; tools and grants; acceptance limits; preflight and READY snapshot. AI copilot suggestions are optional, structured and human-approved.
2. Implement draft save with debounced acknowledgement and revision/ETag conflict recovery without losing typed text. Switching away/back restores exact current task step and approved/unapproved interpretations.
3. Files UI shows hashes, selected purpose, extraction/provenance (PDF page, XLSX sheet/row, DOCX paragraph), progress, rights/PII status and explicit failure/retry. Invalid file cannot be accepted as business evidence.
4. Registry tool suggestions show operation/version/scopes/effect risk and why selected; missing permission triggers request to integration admin, not browser-granted scopes.
5. Preflight shows unmet assertions and responsible person, BTP diff, spend limits and output template. Freeze immutable READY snapshot after domain owner confirmation; editing it creates new revision.

## Definition of Done (local)

1. Full RFQ and certificate fixture journeys through same wizard components; no hardcoded chemistry-only UI.
2. Malformed file, unsupported format, permission denial, missing business rule, 409 stale revision and failed ingest recover correctly.
3. Cannot build without approved snapshot / permitted tool; no accidental holdout exposed to Builder/optimizer via browser.
4. Wizard accessible via keyboard, mobile usable; all screenshots clearly preview until live Task Intake adapter exists.

## Dependencies and blockers

A01 BFF task/registry/artifact typed ports, A02 UI components. Task Intake actual API is not deployed — mark blocked for integration, build against frozen fixtures.

## Suggested execution

1. Define feature's exported view/components/hook props in its own public entry; align to frozen Studio DTOs.
2. Build source-neutral UI including empty/forbidden/stale/partial/error before integrating live BFF.
3. Use synthetic fixtures with explicit DEMO markers in colocated tests only; never put fake values into production widgets.
4. Add negative state tests and style/accessibility checks. Do NOT add/edit global route layout or navigation.
5. Produce PR with allowed diff, test command+actual output, SHA, known blockers and a concise integration handoff for I00.

**Cross-agent change request:** use a feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct edit to other agents' files.
