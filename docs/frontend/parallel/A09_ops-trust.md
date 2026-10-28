# A09: Operator Console modules 11–15: A2A, releases, observability, security and incidents

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A09. **Task:** STU-T11. **Requirements:** AF-REQ-112, 113, 115, 116, 121. **E2E targets:** CJM-E2E-006, 011, 012, 014, 020.

## Exclusive write paths
- apps/studio/src/features/ops/trust/**
- apps/studio/app/[locale]/ops/a2a/**
- apps/studio/app/[locale]/ops/releases/**
- apps/studio/app/[locale]/ops/observability/**
- apps/studio/app/[locale]/ops/security/**
- apps/studio/app/[locale]/ops/incidents/**

## Shared constraints

- Start from I00's single frozen C0 SHA. One branch/PR per agent; no direct merge to main or unapproved ADR decisions.
- Exclusive write paths ONLY; no shared root package/lockfile/Next layouts/central nav, OpenSpec global files, service OpenAPI or Java/Python code. Every other path is integrator or backend-owner property.
- Import public typed @studio/api/contracts/ui/charts/auth exports from C0. Mocks are explicitly DEMO-only in local tests; real capability must be evidence-backed and authorized.
- Screens include loading, empty, forbidden, degraded/stale, partial and error; RU/EN and keyboard/a11y; SCSS Modules and shared tokens.
- Unit/component tests and E2E coverage IDs with actual run logs/commit SHA; only I00 can claim integrated E2E on a common SHA.
- For missing shared type/API/UI component/dependency, create a request inside your own folder; never edit another feature's implementation.

## Deliverables

1. A2A & Bilateral Lab: list deployed Agent Cards, permitted callers, protocol run errors, bilateral scenario state and consent-safe shared history; deep link into A10 scenario UX, without duplicating its editor.
2. Releases & AgentStore: version/channels, signed evidence, approvals, deployment and rollback records; operator request goes through A01 typed BFF and source-owned gate, never direct DB.
3. Traces, Logs & Metrics: authorized correlation, OTel/Langfuse pointers, safe span/timing waterfall if real; redaction and high-cardinality pagination, never a raw admin Langfuse token.
4. Security, Tenants & Audit: access role/scope, consent, signer trusted status and audit events; support tenant-scoped investigation with explicit break-glass design, not automatic full-platform privacy override.
5. Incidents, Alerts & SLO: active incidents with verified source/timestamps, impact, acknowledgment, assignee and safe mitigation request; no invented SLO % when metrics missing.
6. All high-impact actions require server-scoped permission and event audit; charts are source-backed, with accessible table.

## Local acceptance / must test

1. All five routes render correct source-backed data or unavailable; no direct unprivileged access to admin controls.
2. Operator cannot see partner internal traces/holdout or privileged audit of other tenants without explicit scoped permission.
3. Denied release, rollback, raw secret access and incident operation cannot be bypassed via direct HTTP.
4. No dummy uptime or fabricated A2A protocol status; navigation aligns with global I00 route ownership.

## Blocking dependencies / collaboration handoff

A01 BFF security, runtime/AgentStore/A2A/OTel data ports; A02 chart kit; A10 owns actual bilateral creation UI; real production A2A IAM may be missing.

### Implementation order

1. Write feature-local exported component/action interfaces from frozen contracts; do not add root deps without I00 request.
2. Implement source-safe empty/forbidden/unsupported + synthetic fixture variants first.
3. Add intended UI interactions and local typed mocked transport; exercise happy and negative cases.
4. Log any unavailable upstream source as a BLOCKER; never promote unsupported user actions as operational.
5. Submit Draft PR with only owned diff, actual typecheck/lint/unit test outputs, SHA and integration handoff (API/error/state). No global E2E claim.

**Change protocol:** submit feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct change to another owner module, backend or shared contract.
