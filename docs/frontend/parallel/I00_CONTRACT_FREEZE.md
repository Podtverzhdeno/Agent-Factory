# I00 C0 type review and proposed UI contract freeze (2026-10-28)

**Status:** COMPILED PROPOSAL, NOT a deployed BFF contract. C0 source types compile; owner-service APIs and IAM remain missing.

## Reviewed upstream work
- A01 Issue #8: actual CP/Registry controllers inspected; most proposed Studio BFF endpoints are GAP; Registry selection POST is NOT a GET grant. A01's auth/tenant/scope blocking findings are valid.
- A02 Draft PR #19: 6 source-local design artifacts. Approved **15 logical chart taxonomy** and typed SourceStamp/source-backed charts as a UI contract proposal. Not approved as built UI / accessible tested app. ECharts dependency intentionally not added yet; A02 must benchmark.
- A03 Issue #10: 5-step RFQ/certificate design, purpose/provenance files, 409 three-way conflict, READY snapshot + separate Build; accepted as a design input, not as code.

## Frozen UI proposal for interface implementation
- `@studio/contracts` exports SourceState, SourceStamp, SafeError, FeatureAvailability and Task/Agent/Workflow/Run/Evaluation view models; source service OpenAPI is authoritative, no guarantees routes exist.
- `ChartKind` has EXACTLY 15 logical types in `src/contracts/charts.ts`: trend, stacked_bar, horizontal_bar, scatter, heatmap, funnel, timeline, waterfall, sankey, treemap, distribution, gauge, dependency, donut, a2a_sequence. Line/area and histogram/boxplot are subvariants; horizontal error intervals a subvariant. This resolves old ChartSpec mismatch.
- Chart values never come from static showcase as operational metrics. Runtime validation, denominator integrity, source scope, absence of hidden gold and BFF server checks remain A01/A02 implementation.
- Release and Eval statuses are source-authoritative; no fabricated `AVAILABLE`, `PASSED`, `RELEASED`. No secured BFF or real Task Intake is yet running.
- `@studio/api`, `@studio/ui`, `@studio/charts`, `@studio/auth` are fail-closed C0 port placeholders. Feature teams must not invent incompatible global types.

## Missing before live coding acceptance
- Atomic lease coordinator (#18) must be installed on default branch and use approved distinct GitHub actor-role identities; same GitHub actor cannot strongly distinguish independent agent sessions.
- Every coding agent uses C0 SHA after CI success and explicit task claim; initial report/research is not a claim.
- Real Task Intake/Registry grants/AgentStore/runtime/Eval/LiteLLM/A2A integration requires corresponding owner service and ADR ratification.
