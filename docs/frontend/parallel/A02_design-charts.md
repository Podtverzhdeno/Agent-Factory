# A02: Shared SCSS design system, accessible primitives and 15-chart kit

**Status:** assignment READY FOR C0 review; code NOT started. **Owner:** A02; **ID:** STU-T04. **Requirements:** AF-REQ-114, 115, 123. **Test targets:** CJM-E2E-013, 016, 019, 023.

## Exclusive write allowlist
- apps/studio/src/shared/ui/**
- apps/studio/src/shared/styles/**
- apps/studio/src/shared/charts/**
- apps/studio/src/features/chart-showcase/**

## Shared constraints

- Start from integrator-provided C0 BASE_SHA. Branch from that exact revision and open a Draft PR; no direct main merge.
- Read docs/frontend/parallel/README.md; writes ONLY exclusive paths. Do not touch shared package manifests, route layouts/nav, generated source contracts, Java/Python services, docs/parallel/CONTRACTS_V0.md or ADR-0002.
- Call only typed Studio BFF exports. Treat source-authored status, tenant authorization and release/effect proofs as truth. No mock values on production screens.
- All pages: loading/empty/forbidden/unavailable/stale/partial/error; RU/EN keys, keyboard and ARIA semantics, SCSS Modules + theme tokens, responsive states.
- Every mutation follows allowedActions, CSRF/session, stable idempotency/expected revision, 401/403/409/429/503 recovery; frontend flag is no security authority.
- Unit/feature tests colocalized; document real outputs, SHA, skipped checks and missing service dependencies. Never claim full E2E or production readiness.

## Deliverables

1. Create semantic CSS variable token source, limited SCSS utilities, light/dark and reduced motion. Component styles use locally scoped .module.scss; avoid unbounded global selectors or second styling framework.
2. Provide minimal typed UI public API for Button, Input, FormField, FileUpload presentation, Dialog, Tabs, Badge/Status, Alert/Callout, DataTable, Empty/Error/Loading/Stale/Forbidden, Timeline, PageShell slot, Card and source provenance label.
3. Implement typed shared ChartKit with 15 configured templates (line/area, stacked bar, error bars, scatter, heatmap, funnel, Gantt/timeline, waterfall, Sankey, treemap, histogram/box, gauge, dependency, donut and A2A sequence). Prefer Apache ECharts under one adapter; request dependency addition from I00.
4. Each ChartKit config takes a source-stamped validated query/result; show sample_count, timeframe, units, source and last observation; no verified data → empty/unavailable not fake chart. Include accessible table/summary/CSV-safe export (only if permitted).
5. Lazy-load heavy chart engine and variants, paginate/aggregate long series, responsive slots and keyboard safe legend/tooltip controls.
6. Implement reusable chart type/story fixtures marked DEMO strictly within owned directory; no global operational time series invented.

## Definition of Done (local)

1. 15 templates render synthetic fixture and unavailable/partial/unknown variants distinctly; screenshot baselines and accessible table exist.
2. Light/dark tokens, WCAG 2.2 AA target, reduced motion, responsive mobile/desktop, keyboard dialogs and focus checks.
3. One chart engine imported through shared boundary; bundle/large dataset smoke evidence measured, not assumed.
4. All core components can be used by other feature agents without their own duplicated implementations.

## Dependencies and blockers

I00 provides aliases, base module types, package manifest update for ECharts (if chosen), root CSS import. No A02 edit to package.json or global root layout.

## Suggested execution

1. Define feature's exported view/components/hook props in its own public entry; align to frozen Studio DTOs.
2. Build source-neutral UI including empty/forbidden/stale/partial/error before integrating live BFF.
3. Use synthetic fixtures with explicit DEMO markers in colocated tests only; never put fake values into production widgets.
4. Add negative state tests and style/accessibility checks. Do NOT add/edit global route layout or navigation.
5. Produce PR with allowed diff, test command+actual output, SHA, known blockers and a concise integration handoff for I00.

**Cross-agent change request:** use a feature-local CONTRACT_CHANGE_REQUEST.md / UI_REQUEST.md / DEPENDENCY_REQUEST.md, not a direct edit to other agents' files.
