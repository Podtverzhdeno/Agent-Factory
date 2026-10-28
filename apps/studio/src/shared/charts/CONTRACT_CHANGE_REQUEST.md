# CONTRACT_CHANGE_REQUEST — A02 → I00 and A01

**Status:** PROPOSED / requires approval before shared DTO freeze. AF-REQ-114/115/123, STU-T04. No live BFF contracts claimed.

## Conflict requiring a versioned resolution

- docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md: exactly 15 logical templates including horizontal bar (error codes), waterfall/flame.
- openspec/.../spec.md AF-REQ-114: "error bar" alongside 15 templates.
- docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md ChartSpec chartType: "line"|"area"|"stacked_bar"|"scatter"|"heatmap"|"funnel"|"timeline"|"sankey"|"treemap"|"boxplot"|"gauge"|"dependency"|"donut"|"histogram"|"a2a_sequence". No horizontal_bar/waterfall; variants counted differently.

**Request:** I00 freeze a canonical discriminator for **15 logical templates** with explicit line/area, histogram/boxplot, rank/error-interval and Gantt/flame subvariants. Suggested A02 proposal is in A02_CHARTKIT_PROPOSAL.md. Do not silently enlarge "15" to 18 unrelated products or fabricate unsupported native ECharts series.

## Requested BFF read-model commitments

~~~text
GET /api/studio/charts/:chartId?from=...&to=...&granularity=...&cursor=...
- validated chart_kind/schema_version/readonly series
- sourceRefs, revision, sourceAsOf, lastObservedAt, completeness
- sampleCount, denominator, unit, currency?, timezone, time window
- source trust/evidence reference, BFF-calculated effective availability
- redaction scope and allowedActions for table CSV/export/drill down
- safe nextCursor and bounded rows for paginated table
- errors via SafeError; no other-tenant object enumeration
~~~

Server-side schema validation, aggregation, authorization and retention are prerequisites; browser type validation is only defense-in-depth.

## Cases I00 must decide explicitly

1. 200 COMPLETE with legitimate 0 samples: empty table and no graph (never fake zero trend).
2. 200 PARTIAL with some valid rows but missing denominator: no conversion/cost success claim; clear partial label.
3. 200 STALE with sourceAsOf: labelled stale, revision and refresh/reauth action only if allowed.
4. 403: no entity identifier or existence disclosure, clear forbidden view, no export.
5. 401 session change and tenant switch: clear ChartKit cache before new source read.
6. 409 schema revision / unknown backend enum: unsupported, no optimistic success.
7. 429 retry with server backoff, 503 source unavailable: no zero fallback.
8. Missing value or nonfinite number, inconsistent currency/unit/window, negative count, over-cap series → contract error instead of plotting.
9. Sealed holdout/private spans: no row, tooltip, CSV or labels leaked.
10. A2A private lane/event only after verified per-party disclosure scope.

## Coordination

A01 owns transport and auth BFF; I00 owns global DTO contract/alias/typed fixtures; A02 consumes approved outputs. The research branch is not a lease, no owned code exists, no changes to shared spec or backend are proposed directly.
