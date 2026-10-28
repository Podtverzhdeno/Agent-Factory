# Agent Factory Studio — frontend specification index and delivery map

**2026-10-28 · Proposed architecture and implementable CJM.** This repository area contains design/contract documents and isolated work packets, NOT a deployed Studio. Owner ADR-0002 ratification remains pending.

## Read in this order

1. **Canonical requirements / tasks:** [OpenSpec change studio-cjm-parallel](../../openspec/changes/studio-cjm-parallel/) with proposal, design, 26 requirements **AF-REQ-100..125** (including negative WHEN/THEN scenarios), and OPEN implementation tasks **STU-T00..18**. This is the normative SDD delta, subject to owner review.
2. **CJM screen specification:** [CJM_IMPLEMENTATION_BLUEPRINT.md](CJM_IMPLEMENTATION_BLUEPRINT.md) — personas, J00–J13 lifecycle, screen contracts SC-01–11, 16 negative journeys, operator requirements, bilateral variant, states and errors.
3. **Shared frontend port API and tests:** [CJM_UI_CONTRACTS_AND_E2E.md](CJM_UI_CONTRACTS_AND_E2E.md) — BFF read views/actions, user command semantics, chart contracts and proposed **CJM-E2E-001..024**; frozen as proposal for ten coding agents.
4. **Product box / mandatory coverage:** [STUDIO_BOXED_PRODUCT_FEATURES.md](STUDIO_BOXED_PRODUCT_FEATURES.md) — exactly **15 Operator Console modules**, **15 chart templates**, advanced **two-company builder**, and future-only visual LangGraph editor / microfrontends.
5. **Truthful availability:** [STUDIO_FEATURE_CATALOG.json](STUDIO_FEATURE_CATALOG.json) + [STUDIO_CAPABILITY_API_CONTRACT.md](STUDIO_CAPABILITY_API_CONTRACT.md) — product inclusion is not a live feature claim; BFF must compute real availability from verified service evidence + auth.
6. **Parallel implementation:** [parallel/README.md](parallel/README.md) — A01–A10 file-exclusive assignment matrix and I00 integrator. Each Axx has its own packet and a matching [WORK_OWNERSHIP_MANIFEST.json](parallel/WORK_OWNERSHIP_MANIFEST.json).
7. **Integrator playbook:** [parallel/I00_INTEGRATOR.md](parallel/I00_INTEGRATOR.md) — C0 pinned contract/build base, PR intake, merge waves and independent E2E.
8. **Reference architecture:** [STUDIO_SERVICE_COVERAGE.md](STUDIO_SERVICE_COVERAGE.md), [STUDIO_UX_AND_DELIVERY.md](STUDIO_UX_AND_DELIVERY.md), [STUDIO_SCALABILITY_ENGINEERING.md](STUDIO_SCALABILITY_ENGINEERING.md), [AGENT_FACTORY_STUDIO_RFC.md](AGENT_FACTORY_STUDIO_RFC.md), [STUDIO_MVP_SCOPE_DECISION.md](STUDIO_MVP_SCOPE_DECISION.md) — long-term alternatives and early pilot prioritization.

## Which priority wins if older docs disagree?

1. **Owner-ratified ADR and approved upstream OpenAPI** decide physical topology, source authority and safe deployment when they actually exist.
2. **Canonical OpenSpec studio-cjm-parallel** defines proposed Studio behavior and requirement/test mapping pending owner approval.
3. **STUDIO_BOXED_PRODUCT_FEATURES** defines owner's latest target product scope: full Ops console + chart kit mandatory, A/B builder committed advanced, editor/MFE ideas only.
4. **CJM_IMPLEMENTATION_BLUEPRINT + UI_CONTRACTS** define proposed UI interaction and data shapes, adapted to actual service APIs by the integrator.
5. **Parallel packets and ownership manifest** define exclusive write paths; do not rewrite shared code from feature branches.
6. Earlier MVP Scope Decision constrains the **first working pilot**, not the larger target boxed-product feature list.

## Implementation readiness / missing dependencies

| Capability | UI expectation | Actual source readiness |
| --- | --- | --- |
| Task creation/ingestion | Draft → READY, real files | Task Intake/artifact APIs still RFC/partial; no end-to-end product claim |
| Registry + Builder | approved capabilities, immutable AgentSpec | component work exists; full live Registry/Builder pinning not proven |
| Runtime + independent Evaluation | safe sandbox output and signed evidence | isolated signed test seam exists; real tenant KMS and external effects open |
| GEPARD | independent candidate + retest | bounded deterministic mock tested, not live DSPy/GEPA optimization |
| LiteLLM | provider budgets/usage | persistent per-tenant billing/key controls not proven |
| AgentStore/Release | verified → approved → released + rollback | service domain work; full deployment gate E2E pending |
| A2A | authorized calling / advanced bilateral | runtime SDK progress; bilateral only design |
| 15 Ops modules | required target scope, real data + RBAC | varies; must render unavailable until live |
| 15 chart templates | required shared UI capability | no chart implementation in this design PR |
| Visual editor + MFEs | ideas only | intentionally no implementation |

## First execution command to integrator (not automatic)

Freeze C0 SHA + source contract version, assign A01–A10 simultaneously to **disjoint** code folders using each exact packet, then perform staged integration. No frontend agent touches protected common root files, source service code or ADR. Run all required tests on one integrated SHA and report failures honestly. The current documentation does not create agents, spawn background jobs, or modify main.

## Acceptance accounting

- Required OpenSpec specs/tasks must be reviewer approved before treating as implementation baseline.
- Local feature tests ≠ service integration E2E ≠ pilot or production acceptance.
- No false green statuses, silent tenant access, leaked holdout/secrets, irreversible effect claims without external receipt or unauthorized promotion.
- **All implementation tasks remain OPEN in this documentation PR.**
## Live parallel task ownership / activity

- **[Task lease and 2-hour takeover protocol](parallel/TASK_LEASE_PROTOCOL.md)** — claims, UTC event log, heartbeat vs progress, source PR inspection, stale detection, safe generation-fenced handoff.
- **[Live GitHub Issues index](parallel/LIVE_TASK_INDEX.md)** — 10 initialized Issue task records #8–#17. This index is not a live state cache; read each Issue as the latest source.
- **[OpenSpec coordination requirements](../../openspec/changes/studio-cjm-parallel/specs/studio-cjm/spec.md)** — AF-REQ-126..131. STU-T19..23 remain OPEN pending serialized coordinator and executable CI.
