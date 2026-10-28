# A02 ChartKit v0 — 15 source-backed chart contracts

**Status:** PRE-C0 DESIGN ONLY / no executable TypeScript or UI. **Requirement mapping:** AF-REQ-114, AF-REQ-115, AF-REQ-123; CJM-E2E-013/016/019/023. **Issue:** #9 BACKLOG, claim_generation=0. Research branch is NOT the C0 integration base. Do not merge as implementation.

## 1. Non-negotiable data rules

- Data arrives from authenticated Studio BFF only, with server-side tenant/workspace authorization, aggregation, redaction and pagination. Never fetch Java/Python internals, Langfuse admin endpoints or sealed test cases directly from browser.
- A chart must have an explicit **source reference, time range + timezone, units, sample count/denominator, source timestamp, schema revision, completeness and permission**. Missing source does not mean zero, and a revoked grant immediately prevents cached data from being displayed.
- Source state and page state are separate: COMPLETE, PARTIAL, STALE, UNAVAILABLE, UNSUPPORTED are from SourceStamp; forbidden/HTTP error/empty/loading are presentation/error boundaries.
- PASSED, RELEASED, measured cost and business KPI only show if certified by their authoritative upstream service. The chart library never assigns those statuses.
- Accessible table + textual summary exist without the chart engine; CSV/exports only through an authorized, server-scoped action. Never export hidden holdout rows or private tenant values.

## 2. Proposed public ChartView API and data model (discussion, not compiled)

~~~ts
type ChartKind =
  | "trend" | "stacked_bar" | "horizontal_bar" | "scatter"
  | "heatmap" | "funnel" | "timeline" | "waterfall" | "sankey"
  | "treemap" | "distribution" | "gauge" | "dependency"
  | "donut" | "a2a_sequence";

interface ChartMeta {
  chartId: string;
  titleKey: string;
  kind: ChartKind;
  schemaVersion: string;
  queryKey: string; // stable authorized BFF query identity, no raw credentials
  sourceRefs: readonly string[];
  window: {
    from: string; to: string; timezone: string; granularity: string;
  };
  unit: string;
  currency?: string | null; // ISO 4217 if monetary
  sampleCount: number | null;
  denominator?: number | null;
  sourceAsOf: string | null; // RFC3339 UTC
  lastObservedAt: string | null;
  revision: string | null;
  redactionLevel: "PUBLIC" | "TENANT" | "OPERATOR_REDACTED";
  completeness: "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "STALE" | "UNSUPPORTED";
}
interface ScalarPoint { key: string; label: string; value: number | null; }
interface TimePoint { at: string; value: number | null; count?: number | null; }
interface MatrixCell { xKey: string; yKey: string; value: number | null; }
interface FlowEdge { from: string; to: string; value: number; }
interface SwimlaneEvent {
  eventRef: string; actorRef: string; recipientRef: string | null;
  occurredAt: string; eventType: string; disclosed: boolean;
}
interface ChartTable {
  captionKey: string;
  columns: readonly { id: string; headingKey: string; unit?: string }[];
  rows: readonly Record<string, string | number | null>[];
  nextCursor: string | null;
}
type ChartPayload =
  | { kind: "trend"; variant: "line" | "area"; points: readonly TimePoint[] }
  | { kind: "stacked_bar"; categories: readonly string[]; series: readonly { key: string; values: readonly (number | null)[] }[] }
  | { kind: "horizontal_bar"; points: readonly ScalarPoint[]; variant: "rank" | "error_interval"; intervals?: readonly [number, number][] }
  | { kind: "scatter"; points: readonly { id: string; x: number; y: number; size?: number | null }[] }
  | { kind: "heatmap"; cells: readonly MatrixCell[] }
  | { kind: "funnel"; stages: readonly { id: string; count: number; denominator: number | null }[] }
  | { kind: "timeline"; intervals: readonly { id: string; from: string; to: string; lane: string }[] }
  | { kind: "waterfall"; steps: readonly { id: string; delta: number; total?: number | null }[] }
  | { kind: "sankey"; nodes: readonly { id: string; label: string }[]; edges: readonly FlowEdge[] }
  | { kind: "treemap"; leaves: readonly { id: string; parentId: string | null; value: number }[] }
  | { kind: "distribution"; variant: "histogram" | "boxplot"; bins: readonly { x: number; count: number }[]; quartiles?: readonly number[] }
  | { kind: "gauge"; current: number; limit: number; unit: string }
  | { kind: "dependency"; nodes: readonly { id: string; label: string; state: string }[]; edges: readonly { from: string; to: string }[] }
  | { kind: "donut"; slices: readonly ScalarPoint[] }
  | { kind: "a2a_sequence"; events: readonly SwimlaneEvent[] };

type ChartResult =
  | { state: "ready"; meta: ChartMeta; payload: ChartPayload; table: ChartTable }
  | { state: "partial" | "stale"; meta: ChartMeta; payload: ChartPayload; table: ChartTable; reasonCode: string }
  | { state: "empty"; meta: ChartMeta; table: ChartTable }
  | { state: "unavailable" | "unsupported" | "forbidden" | "error"; meta?: ChartMeta; reasonCode: string }
  | { state: "loading" };
interface ChartViewProps {
  result: ChartResult;
  locale: "ru" | "en";
  showTableByDefault?: boolean;
  onRequestMoreRows?: (cursor: string) => void; // authorized BFF paging only
  onOpenSource?: (sourceRef: string) => void; // no fabricated deep link
}
~~~

**Implementation caveat:** these are candidate presentation types. I00 must reconcile them with frozen ChartSpec/SourceStamp, literal backend contracts and exact schema validation. The discriminated union is not a replacement for runtime validation on untrusted JSON. Monetary totals remain decimal strings at the BFF/domain boundary; do not directly convert arbitrary prices to JS floats for trusted financial claims.

## 3. Fifteen chart templates and source gates

| # | Chart kind / subvariant | Authorized data source | Must be present to enable visual | Null/degraded behavior |
| --- | --- | --- | --- | --- |
| 1 | Trend (line/area) | Runtime + independent Evaluation | real bucketed outcome counts, timestamps, timezone and stable sample denominator | gaps remain null; incomplete bucket marked partial |
| 2 | Stacked bar | LiteLLM gateway/usage reconciliation | per-model tokens/cost grouped by same currency, period and invoice-backed usage | no cost if billing inconsistent or unknown |
| 3 | Horizontal bar / error intervals | independent Evaluation safe failure taxonomy | error-code counts or measured confidence bounds with method + n | never display hidden dataset labels or inferred intervals |
| 4 | Scatter/bubble | independent Evaluation + trusted cost | candidate quality, billed spend and matched cohort/sample size | x/y absent → unavailable, no artificial zeros |
| 5 | Heatmap | aggregated Evaluation regression matrix | version × safe failure class with count and common denominator | withheld gold stays masked; missing cells not zero |
| 6 | Funnel | Task Intake → Orchestrator → Evaluation → AgentStore | source-verified stage counts, one population and fixed window | stages incomplete → partial; do not claim conversion |
| 7 | Timeline/Gantt | Orchestrator/Runtime events | real start/end or span time, consistent run ID, source timezone | missing end → in-progress/unknown; no fabricated duration |
| 8 | Waterfall/flame breakdown | sanitized OTel/Langfuse trace aggregates | nonoverlapping approved phase/latency summaries with timestamps | missing spans → partial, no invented total |
| 9 | Sankey | gateway routing + Runtime tool invocation aggregates | directed audited edges, source-specific units and grant | no raw agent-to-agent private route details |
| 10 | Treemap | reconciled usage/BFF project-scoped aggregation | nonnegative costs and authorized tenant/project/agent hierarchy | cross-tenant leaf must be suppressed before browser |
| 11 | Distribution (histogram/boxplot) | Runtime run samples | bin bounds, sample_count and unit; quartiles computed server-side | no fabricated p95/median for sparse samples |
| 12 | Gauge/progress | persisted budget owner | authoritative current and maximum limit, same unit/window | missing limit → unavailable, not 100% |
| 13 | Dependency graph | service registry + observed health | source topology revision, observed health for each permitted edge | unobserved link styled unknown, not green |
| 14 | Donut/pie | AgentStore/CP authoritative statuses | small bounded known categories, exact counts/denominator | unknown status gets separate labelled category |
| 15 | A2A sequence/swimlanes | signed and policy-filtered A2A events | event timestamps, sender/recipient and granted disclosure scope | redacted messages remain redacted; no secret hover details |

These are 15 **logical templates**, not 15 independent chart engines. Variant counts (line vs area, histogram vs box) do not alter the required total.

### Contract discrepancy requiring I00 decision

The product-box taxonomy in STUDIO_BOXED_PRODUCT_FEATURES.md has horizontal failure bar and waterfall, while the proposed ChartSpec union in CJM_UI_CONTRACTS_AND_E2E.md contains separate line/area and histogram/boxplot but **no** horizontal_bar or waterfall. AF-REQ-114 separately says "error bar"; the A02 work packet mentions "error bars". I00 should freeze an explicit versioned mapping (including error intervals) rather than let separate teams add custom strings ad hoc. Our proposed ChartKind is not approved canonical schema.

## 4. Rendering, security and accessibility

1. BFF returns safe filtered/aggregated data; ChartKit revalidates discriminant, timestamps, finite ranges, row/point limits, unit/denominator and provenance. Unknown chart kind or unsupported schema produces UNSUPPORTED.
2. No visual chart without adequate source evidence. On complete source and 0 verified samples, display **empty**, not an invented all-zero series. On partial/stale source with safe data, allow visibly labelled partial/stale with exact sourceAsOf; block misleading aggregate KPIs.
3. Label source/service, timezone, period, unit, sample count, denominator and last observation. Include accessible HTML table with caption and a concise textual summary, available without loading ECharts.
4. Cross-tenant and privilege checks occur in BFF and source owner, not in ChartView. Safe placeholders cannot leak forbidden object IDs via errors, tabular exports or tooltips.
5. Use keyboard-accessible legend and focusable data-point summaries; tooltip data also available in table; announce loading→ready/error only on material status change. Pattern/shape/text accompany color.
6. Responsive and dark/light using A02 tokens, with low-motion path and rendering mode chosen by actual benchmark. Never let mouse-only tooltip be the sole way to inspect values.
7. ECharts adapter is client-side lazy loaded only when a trusted series is available; all direct ECharts imports remain in shared/charts. Prefer echarts/core explicit charts/components/renderers registered in one module; do not claim bundle gains without profiling.
8. Dense series: server bounds page/window and aggregation; chart payload cap (to agree with I00) and separate authenticated cursor for table rows. Avoid shipping 10k raw spans, hidden holdout outcomes or unrestricted trace graphs to browser.
9. Reconciliation for costs, percentage denominators and ratings is computed by authoritative source/BFF; no client-side averaging of incompatible cohorts or decimal money.

## 5. I00 integration and backend requests

- **CONTRACT_CHANGE_REQUEST:** resolve chart enum mismatch and publish shared chart schema version + validated BFF endpoint response, error envelope, effective capability and export permission; include complete/partial/unknown cases.
- BFF /api/studio/charts/:chartId must return server-authored sourceAsOf, stamp/completeness, queryKey, sampleCount, denominator, sourceRefs, unit/currency/time window, redaction class and safe aggregate rows.
- Define error handling for 401 (reauth), 403 (no existence leak), 409 (schema/source revision mismatch), 429 (backoff), 503 (source unavailable), and stale cached series on tenant switch.
- I00 owns @studio/charts alias, root imports, shared DTO, pnpm and the real integration smoke/CI matrix. No changes to those files from A02.
- Dependencies: see DEPENDENCY_REQUEST.md (one ECharts engine, SCSS support and test runner). No unreviewed package additions.

## 6. Acceptance evidence to collect after granted C0/lease

- 15 kinds × (verified synthetic preview, empty, partial, error/unavailable) with fixtures explicitly marked DEMO; each has accessible table and source label.
- Actual BFF fixtures for at least 401, 403, stale tenant cache, unknown status, missing denominator, divergent currencies, revoked permission, no-sample, large trace.
- Keyboard, Escape/focus, screen reader table/summary, dark/light and reduced motion on mobile and desktop.
- Load 10k aggregated points with repeatable browser environment; record JS heap, interaction delay, hydrated chunk bytes and render time; do not substitute a guessed performance number for measured evidence.
- Integration E2E CJM-E2E-013/016/019/023 on pinned merged C0 code revision belongs to I00; no tests currently executed.
