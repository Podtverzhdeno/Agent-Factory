# A02 local verification matrix — prepared before C0

**Status:** PROPOSED tests, NOT RUN. No browser harness, shared DTO implementation or C0 base committed yet. Draft-only synthetic showcase must be clearly watermarked DEMO and must never be mounted under a live operator/business route.

## 1. Required suites after authorized claim

| Suite | Scope | Criteria | Test ID / evidence |
| --- | --- | --- | --- |
| TYPE-001 | All 15 discriminated-union chart payloads | exact exhaustive switch, invalid enum rejected | typecheck/TS exact SHA |
| CHART-001..015 | each of 15 logical kinds | valid synthetic preview, accessible source-stamped table, no unsafe hover details | AF-REQ-114; CJM-E2E-013 |
| STATE-001..015 | each kind with no source/denominator | unavailable/empty, no fabricated zero or success | AF-REQ-114 |
| STATE-016..030 | each kind with partial/stale/missing bucket | explicit warning, timestamp and no false aggregate | AF-REQ-114 |
| STATE-031..045 | each kind invalid schema/value/unsupported enum | safe unsupported/error, no crash/leak | AF-REQ-114 |
| ROLE-001 | cross-tenant chart ID direct URL | BFF 403 without existence leak, no cached data | AF-REQ-115; CJM-E2E-006 |
| ROLE-002 | operator-only chart from customer role | forbidden action and export cannot be invoked | AF-REQ-115 |
| ROLE-003 | tenant switch, revoked grants, logout | cached chart and table cleared before new actor view | AF-REQ-115 |
| EXPORT-001 | permitted CSV export | same scoped rows and units, escaped CSV formula prefixes | AF-REQ-115 |
| EXPORT-002 | denied or holdout export | no export link, no raw data via details / tooltip / logs | AF-REQ-115 |
| PERF-001 | bounded 10k-point aggregate fixture | no unbounded raw span fetch, record real heap/parse/render metrics | CJM-E2E-016 |
| PERF-002 | 15 charts lazy page, repeat unmount | disposed renderer and observers; record initial vs loaded chunk bytes | AF-REQ-115 |
| COST-001 | LiteLLM cost absent/unreconciled | no cost-per-success or revenue chart, reason visible | CJM-E2E-019 |
| A11Y-001 | tabs, dialog, tooltip and file picker keyboard-only | Enter/Space, arrow/Home/End, Escape and focus return as appropriate | CJM-E2E-023 |
| A11Y-002 | table and chart at 360, 390, 768, 1440px | accessible caption, source/unit/time, no clipped controls | CJM-E2E-023 |
| A11Y-003 | dark/light, reduced motion, high contrast | contrast measurement, no animation-only meaning | CJM-E2E-023 |
| I18N-001 | RU/EN long labels, numbers/timezone | no clipping; symbols/tables localized and safe | AF-REQ-123 |
| NETWORK-001 | 401, 403, 409, 429, 503 | explicit state/retry/permission; no false PASS | AF-REQ-114/115 |

### Logical chart-kind coverage

1. trend (line/area)
2. stacked_bar
3. horizontal_bar / error intervals (I00 enum decision pending)
4. scatter
5. heatmap
6. funnel
7. timeline / Gantt
8. waterfall / flame
9. sankey
10. treemap
11. distribution (histogram / boxplot)
12. gauge
13. dependency
14. donut
15. a2a_sequence

Chart fixtures: positive DEMO, empty, partial, stale, unavailable, malformed. The words VERIFIED/PASSED/RELEASED in **synthetic** fixtures must be prefixed with DEMO and never used to imply successful production execution.

## 2. Negative dataset specification

Create only synthetic, non-identifiable fixtures after C0:
- Missing denominator, missing sourceAsOf, missing timestamp, missing unit, invalid ISO date, NaN/Infinity, negative sample count.
- Currency mismatch USD/EUR, incompatible timeframe/granularity, duplicated bucket, unsorted event, broken edge/node graph.
- Tenant A data accidentally referenced in B chart (should be blocked at BFF + checked as browser absence).
- Redacted holdout id, unsafe HTML tooltip label, CSV injection prefix (=, +, -, @).
- 10001-point synthetic trace with authenticated server pagination, A2A event with consent revoked mid-session.
- Two distinct read models: customer analytics versus privileged operator. No automatic privilege escalation from a frontend button.

## 3. Test technique and evidence

- Component tests colocated under A02-owned directories, not global tests/e2e. I00 owns integrated Playwright.
- UI stories require explicit visual DEMO watermark and name of synthetic fixture; never show fake customer SLAs, generated budgets or payouts as live.
- Capture exact command, exit code, test count, failures, skipped tests, runner version, baseline SHA and branch; no "pass" without actual runner output.
- For WCAG 2.2 AA use automated axe plus manual focus, screen reader and keyboard review; attach measured contrasts in both themes, do not assume token colors pass.
- For perf report JS initial/loaded chunk bytes, browser heap, render latency, longest main-thread task and memory after unmount. Compare on identical browser/device hardware, don't assert any magic threshold before baseline.
- For large-series source guard: server must paginate or aggregate; client may render a bounded set and show the full table cursor only with authorization.
- Never treat component checks as true backend E2E or as source-verified business events.

## 4. Current execution ledger (truthful)

| Item | Current |
| --- | --- |
| Source branch | design/frontend-studio-rfc-20261028 (documentation, NOT frozen C0) |
| Issue #9 | BACKLOG / WAITING_FOR_C0; current_owner=null; claim_generation=0 |
| Coordinator | NOT_DEPLOYED, no authorized lease |
| Shared studio tsconfig / package / root skeleton | missing on checked design/main refs |
| Current A02 executable tests | NOT RUN (none implemented) |
| CI/coverage/browser screenshots | NOT AVAILABLE |
| Security/tenant checks | SPECIFIED ONLY, not runtime-executed |
| ADR-0002 | owner review pending |
| Next permission | I00 freezes C0 / DTO / claim coordinator; then A02 receives GRANTED lease |

## 5. Integration handoff checklist to I00

- Resolve chart schema enum mismatch (horizontal bar, error intervals, waterfall) and freeze source/version fields.
- Publish @studio/ui and @studio/charts aliases, theme import and SCSS module compiler.
- Approve ECharts package/license and pinned lockfile in I00-owned files.
- Provide typed synthetic fixture BFF and authenticated tenant-switch state tests.
- Enable path-ownership CI and issue-lease generation fencing before accepting an implementation branch.
- Schedule real CI with browser/devtools measurements; operator chart source readiness is independent of generic renderer readiness.
