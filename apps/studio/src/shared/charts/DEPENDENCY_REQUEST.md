# DEPENDENCY_REQUEST — A02 → I00

**Task:** STU-T04 / Issue #9. **Request status:** PROPOSED; not installed, not authorized. **Precondition:** I00 C0 and lease before code.

## Request 1 — a single chart engine

- **Package:** echarts
- **Candidate version:** 6.1.0 (published 2026-05-18 per upstream changelog; npm latest checked 2026-10-28).
- **License:** Apache-2.0 (review license, NOTICE and nested dependencies before approval).
- **Usage:** ECharts 6 core with explicit needed chart/component/renderer registrations only, imported dynamically inside @studio/charts on client. No direct imports from features.
- **Need:** one engine across trend, stacked/horizontal bar, scatter, heatmap, funnel, timeline, waterfall, sankey, treemap, distributions, gauge, dependency, donut and sequence. Some (waterfall/A2A sequence/error intervals) require custom/overlaid series with tested semantics rather than fictitious native chart support.
- **References:** https://echarts.apache.org/en/changelog.html ; https://www.npmjs.com/package/echarts ; https://apache.github.io/echarts-handbook/en/basics/release-note/v6-upgrade-guide/
- **Security:** no user-supplied HTML in formatter/tooltip; escape labels, never include secret/holdout/raw traces; CSP review for rendering path.
- **Bundle impact:** UNKNOWN until Next.js production build. Evaluate core tree-shaken lazy chunk vs baseline with report of browser-loaded gzip bytes and total JS; reject if UI starts loading charts on pages without permitted chart data.
- **Operational risk:** larger vendor chunk, SSR/browser lifecycle differences, huge allocations from raw series, complexity of custom series. Mitigate SSR-safe client-only boundary, explicit dispose, ResizeObserver teardown, budget-tested server aggregation, table fallback.
- **Decision requested of I00:** approve/select version and update apps/studio/package.json + lockfile ONLY after C0; own dependency scan and third-party notices.

## Request 2 — SCSS compiler

- **Package:** sass **only if missing from I00 root skeleton**; version pinned by I00 to a supported nondeprecated build.
- **License:** MIT (verify pinned distribution).
- **Purpose:** compile .module.scss and guarded local mixins. No second CSS-in-JS framework.
- **Bundle/runtime:** build-time dependency; verify outputs and no shared global leakage.
- **Decision requested:** approve toolchain and lint baseline in I00-owned package/CI. A02 does not modify package manifests.

## Tests/tools to be supplied or approved

React/TypeScript strict Next.js base, Vitest/RTL (or existing single component runner), axe-core and Playwright integrated visual/keyboard checks; do not duplicate runners. Freeze alias @studio/charts and @studio/ui first.

## Acceptance before adding any dependency

1. I00-approved C0 SHA and versioned chart data DTO contract.
2. License/security scan and lockfile pinned.
3. Measured initial/page-loaded/loaded-chart chunk impact in production build, large-series memory and unmount cleanup.
4. Test quality: 15 kinds; permitted vs forbidden source, missing denominator, overflow bounds, preview labelling, table fallback and screen reader.
5. Rollback: remove adapter import from I00 route composition and fall back to source-labelled tables; no business state changes.

**No dependency installed; no build-size or perf PASS claimed.**
