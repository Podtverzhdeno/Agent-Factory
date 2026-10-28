# RFC — Scalable frontend engineering standard for Agent Factory Studio

**Status:** PROPOSED / requires architectural review, not a deployed frontend.  
**Date:** 2026-10-28  
**Owner scope update:** [`STUDIO_BOXED_PRODUCT_FEATURES.md`](STUDIO_BOXED_PRODUCT_FEATURES.md) is the authoritative target-scope override: 15-section Operator Console and a large shared chart kit are mandatory product modules; twin-company builder is a committed advanced module; visual LangGraph editor and microfrontends remain ideas only. Initial wiring may remain staged pending real APIs and data. 
**Strict sequencing correction (2026-10-28):** [`STUDIO_MVP_SCOPE_DECISION.md`](STUDIO_MVP_SCOPE_DECISION.md) is the canonical implementation priority. pnpm workspaces/Turborepo, Redis/SSE fanout, separate BFF deployment, large ops console and multiple packages are **NOT** P0 requirements unless a measurable trigger occurs. TypeScript strict, SCSS Modules, real RBAC, safe DTOs and tests remain P0.  
**Product context:** Agent Factory Studio (customer Business Workspace + privileged Operator Console) integrating Factory Orchestrator, Registry, Builder, Runtime, Evaluation, GEPARD, LiteLLM, AgentStore, A2A and observability.  
**Supersedes no owner decision:** ADR-0002 still PENDING. This document commits no production topology without owner approval.

## 1. What "scaling" means

Scaling must be designed across **six independent axes**, not reduced to CSS or number of browser users:

1. **Product coverage:** add new microservices (Soup, bilateral A2A), screens, integrations and data types without changing existing business modules.
2. **Frontend team:** simultaneous ownership of 10–20 feature domains, isolated review/tests and predictable boundaries without a shared mega-component.
3. **Browser performance:** large agents, thousands of runs, long timelines, live traces, several simultaneous charts and responsive use without heavy initial JavaScript.
4. **API and event throughput:** thousands of authorized user sessions, SSE reconnect bursts, backpressure, pagination and BFF service isolation.
5. **Multi-tenant security:** increasing tenants without leaks through caches, event subscriptions, search, IDs, logs, uploads or signed artifact URLs.
6. **Deployment and operations:** independent releases/rollbacks, CI caching, feature flags, staged rollout, real metrics, SLO/alerting and controlled migrations.

A visually fast frontend that leaks other tenants' audit traces or marks a candidate RELEASED is a failed architecture.

## 2. Decisions and alternatives

| Topic | Default proposal | Why | Avoid / defer |
| --- | --- | --- | --- |
| Language | TypeScript for all browser and BFF application code | Runtime-safe modeling, contracts, refactoring and large-team boundaries | broad \`any\`, hand-copied Java/Python DTO interfaces |
| Web | React + Next.js App Router | SSR/public shell, route-based chunking, auth-capable server runtime | moving business orchestration into Next actions |
| Styling | **SCSS Modules** for local component styles + CSS custom properties for themes | Encapsulation, expressiveness for dense enterprise widgets, static CSS, theme portability | global selectors, unlimited mixin inheritance, giant universal SCSS file |
| Primitives | accessible React component primitives + our own \`@agent-factory/ui\` | Consistent interactions and keyboard semantics | vendor styling as a permanent system of record |
| Layout | CSS Grid/Flexbox/container queries; design tokens | Flexible responsive inspector, wizard, tables, charts | fixed px layouts and JS-only breakpoints for ordinary layout |
| Monorepo | pnpm workspaces; Turborepo for TS task graph and cached outputs | Shared UI/SDK, incremental CI and version cohesion | using Turbo as replacement for Java Maven/Python tooling |
| Boundaries | modular-monolith frontend + public BFF | Easier cross-feature navigation, consistency, debugging | microfrontend federation at MVP; too much duplicated auth/runtime/state |
| State | URL (search, filters, sort) + TanStack Query (server state) + local component state | Refresh/deep-link correctness and bounded client state | giant global Redux store mirroring all backend databases |
| Contracts | OpenAPI-generated TS types/clients from *versioned* Java/Python specifications; Zod validators at selected trust boundaries | Detect drift before runtime; safe gradual backends | declaring type safety from an unchecked \`fetch().json() as X\` |
| Events | server-authorized BFF SSE projections and snapshot refetch; fallback polling | Operations are server-to-browser stream; robust and easy to cache/observe | browser directly consuming Kafka / exposing private signing evidence |
| Testing | Vitest + Testing Library + MSW + Playwright + axe checks + component visual regression | Proves behavior, contract and accessible UI | brittle screenshot-only acceptance |
| Monitoring | OTel BFF spans + browser Web Vitals/errors + feature and API metrics | Ties Studio problems to service issues without recording raw secrets | accidental PII, prompts or gold material in traces |
| Runtime config | validated server-only config and environment-specific flags | Safe staged rollout and rollback | build-time client secrets or frontend deciding release permissions |

**Tailwind:** optional for limited prototypes only, **not** the preferred baseline. Do not mix Tailwind utilities, global BEM rules and SCSS Modules indiscriminately. One chosen styling policy must be enforced. Avoid CSS-in-JS runtime styling for large critical-path tables/inspectors by default.

**Microfrontends:** NOT initially. Reconsider only if multiple teams need independently shipped bundles with distinct SLA/deployment cadence, strong isolation and measurable release bottlenecks; first exhaust package/module boundaries.

**Separate Studio BFF service:** domain boundary from day one, physical process may initially be Next.js server handlers; extract into a stateless TS service when independent scaling, streaming connection counts, traffic mix or organizational ownership justifies it. Never put real Orchestrator state machine in the BFF.

## 3. Repository architecture and ownership

Java/Python microservices and their tests remain in service-owned paths. TypeScript monorepo lives alongside them:

~~~text
Agent-Factory/
  apps/
    studio-web/                  # Next.js, SSR/RSC UI, no business DB access
      app/[locale]/w/[workspaceId]/...
      app/[locale]/ops/...       # additional authorization boundary
      src/
        app-providers/
        features/
          task-intake/
          agent-builder/
          workflow-observation/
          agent-mission-control/
          run-inspector/
          tool-registry/
          quality-evaluation/
          gepard-experiments/
          model-usage/
          releases/
          a2a-clients/
          operations/
        entities/
          workspace/
          task/
          agent/
          run/
          evaluation/
          release/
        widgets/
          global-nav/
          activity-timeline/
          agent-graph/
          incident-drawer/
        shared/
          auth/                  # presentation permissions only
          ui/
          styles/
          hooks/
          lib/
          i18n/
    studio-bff/                  # optional later separate process, contract-ready boundary
      src/
        http/
        auth/
        read-models/
        service-adapters/
          control-plane/
          registry/
          builder/
          runtime/
          evaluation/
          optimizer/
          litellm/
          agent-store/
          observability/
        events/
        policy/
        telemetry/
  packages/
    ui/                          # @agent-factory/ui
      src/components/
      src/tokens/
      src/styles/
    design-tokens/               # @agent-factory/design-tokens
    api-contracts/               # generated DTOs; do not hand-edit
    api-client/                  # typed HTTP wrappers, timeout/errors
    domain-models/               # Studio view models, NO backend state ownership
    eslint-config/
    tsconfig/
    test-utils/
  services/
    factory-orchestrator/ ...    # Java
    tool-mcp-registry/ ...
    agent-builder/ ...
    agent-runtime/ ...
    evaluation/ ...
    gepard-optimizer/ ...
    ...
  pnpm-workspace.yaml
  turbo.json
~~~

Do not create every optional directory prematurely; this is a target module map, not a request for empty scaffolding. Avoid \`shared/utils\` becoming a dumping ground: use precise public APIs and package names.

### Strict dependency direction

\`app routes → page widgets → features → entities → shared\` (higher imports lower only); cross-feature use goes through a documented public API and explicit composition in route/page, **never** \`features/quality/internal/**\` imported by \`features/agent-builder/**\`.

- \`packages/ui\` must never depend on backend-specific DTOs, business permissions or any feature module.
- \`api-contracts\` is generated from service-owned OpenAPI and never depends on React.
- \`api-client\` owns transport and typed error handling; \`domain-models\` maps server DTOs into safe UI projection types.
- Feature modules own their hooks, tests, styles, locale keys and loading/error/empty states.
- \`BFF/service-adapters\` depend on API contracts, not on React components. Backend code never imports frontend packages.
- Enforce with ESLint no-restricted-imports, dependency-cruiser or equivalent, no circular dependencies and named package exports. CODEOWNERS for app/shared contracts, approvals for auth/release/tenant abstractions.

### Scaling teams

Suggested owners: **Creation** (Task Intake/Builder/Registry), **Execution** (Runtime/A2A/run inspector), **Quality** (Evaluation/GEPARD/LiteLLM), **Trust** (release/policy/AgentStore), **Platform** (BFF/auth/observability/design system/CI). One small team can initially own all; boundaries make later splitting possible without rewriting frontend.

## 4. TypeScript engineering standard

### Compiler and type discipline

- \`strict: true\`, \`noUncheckedIndexedAccess: true\`, \`exactOptionalPropertyTypes: true\`, \`noFallthroughCasesInSwitch: true\`, \`noImplicitOverride: true\`, \`useUnknownInCatchVariables: true\`, \`noEmitOnError: true\`.
- \`skipLibCheck\` only as a documented dependency trade-off, never a replacement for own types.
- \`no-explicit-any\` lint with focused justified exceptions; \`unknown\` + schemas for inbound API; explicit return types for exported interfaces and auth/release/effects boundaries.
- Strict discriminated unions for statuses **per bounded context**. \`EvaluationRun PASSED\` does not imply \`AgentStore RELEASED\`.
- \`never\` exhaustiveness checks for legal transition mapping; unrecognized future backend statuses become \`UNKNOWN_UNSUPPORTED_VERSION\`, never PASS.
- Branded/opaque IDs for agent/run/workflow/evaluation/spec versions where appropriate; do not mix identifiers through plain string parameters at trust boundaries.
- Domain enums and schemas **generated from authoritative backend contract**; do not write \`type Status = "RELEASED" | ...\` independently in every feature.
- React server and client code separated; mark server-only modules and avoid bundling crypto/server tokens in client bundles.

Illustrative (not generated from live OpenAPI):

~~~ts
type QualityResult =
  | { kind: "PASSED"; evidenceRef: string; independent: boolean }
  | { kind: "FAILED"; reasonCodes: readonly string[] }
  | { kind: "BLOCKED"; requiredAction: string }
  | { kind: "UNAVAILABLE"; source: string }
  | { kind: "UNKNOWN_UNSUPPORTED_VERSION"; rawStatus: string };

function renderStatusLabel(result: QualityResult): string {
  switch (result.kind) {
    case "PASSED": return result.independent ? "Независимая проверка пройдена" : "Требуется независимая проверка";
    case "FAILED": return "Проверка выявила ошибки";
    case "BLOCKED": return result.requiredAction;
    case "UNAVAILABLE": return "Сервис недоступен";
    case "UNKNOWN_UNSUPPORTED_VERSION": return "Неподдерживаемый формат";
    default: {
      const impossible: never = result;
      return impossible;
    }
  }
}
~~~

### Project References / TS build scaling

- Base TS configs centrally in \`packages/tsconfig\`; library packages with \`composite\`, \`declaration\`, \`declarationMap\`, \`incremental\` as applicable.
- Use \`tsc -b\` and references for TS libraries when package graph justifies; this enables incremental checking without pretending the Next.js application is a \`tsc\`-emitted distributable library.
- Next.js app typecheck via \`tsc --noEmit\` and Next build; package exports explicit. \`moduleResolution: "Bundler"\` for browser/Next packages, \`NodeNext\` in standalone Node BFF when relevant; don't combine without explicit configs.
- API contract generation is pinned by service OpenAPI source SHA; regenerate in CI and fail if committed generated SDK stale.
- Contract version mismatch results in safe \`unsupported\` screen state, not app crash or optimistic release.

## 5. SCSS Modules + design token system

### Theming architecture

Three layers, each with a clear responsibility:
1. **Design tokens**: semantic colors, spacing, typography, elevation, radius, animation, z-index and layout density. Source JSON/TS → generated CSS variables + optional SCSS token accessors. No arbitrary hex colors inside features.
2. **Global stylesheet** (small): reset, fonts/typography defaults, root tokens and theme overrides \`[data-theme="dark"]\`, focus utilities, reduced motion and print concerns.
3. **SCSS Modules per component**: \`Component.module.scss\` sets local layout/visuals using CSS custom properties, Sass module \`@use\`, logical properties and container queries. No feature-wide global selectors.

Theme switching uses \`data-theme\` on the app root + CSS variables and honors OS preference before explicit authorized user choice. No full stylesheet rebuild per theme. Semantic status tokens include color AND icon/text; accessibility must not depend on color alone.

Illustrative tokens (not approved branding):

~~~scss
/* packages/design-tokens/src/tokens.css */
:root {
  --af-color-background: #ffffff;
  --af-color-surface: #f6f8fb;
  --af-color-text: #1d2735;
  --af-color-border: #dce4ed;
  --af-color-primary: #1264d8;
  --af-color-positive: #16734a;
  --af-color-warning: #8a5a00;
  --af-color-danger: #b52634;
  --af-space-1: 0.25rem;
  --af-space-2: 0.5rem;
  --af-space-3: 0.75rem;
  --af-space-4: 1rem;
  --af-space-6: 1.5rem;
  --af-radius-md: 0.75rem;
}
:root[data-theme="dark"] {
  --af-color-background: #101722;
  --af-color-surface: #182331;
  --af-color-text: #edf2f8;
  --af-color-border: #354456;
  --af-color-primary: #7bb1ff;
  --af-color-positive: #6bd1a1;
  --af-color-warning: #f3c270;
  --af-color-danger: #ff9c9f;
}
~~~

~~~scss
/* features/workflow-observation/WorkflowStage.module.scss */
.stage {
  display: grid;
  gap: var(--af-space-2);
  padding: var(--af-space-4);
  background: var(--af-color-surface);
  color: var(--af-color-text);
  border: 1px solid var(--af-color-border);
  border-radius: var(--af-radius-md);
  container-type: inline-size;

  &[data-state="blocked"] {
    border-inline-start: 0.25rem solid var(--af-color-danger);
  }

  @container (min-width: 38rem) {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stage { transition: none; }
}
~~~

### Rules to stop CSS growth and regressions

- Require SCSS Modules on UI components. Allowed exceptions: one root reset/tokens file, third-party CSS boundary with documented reason. Stylelint/Prettier enforce format, selector specificity, nesting depth and duplicate properties; no \`!important\` except reviewed integration cases.
- No deep \`@extend\` inheritance chains, massive nested selectors, or \`@import\` deprecated Sass syntax; use \`@use\`/\`@forward\` for reusable mixins and compile-time helpers.
- Use CSS variables for runtime themes; Sass variables/mixins only for compile-time algorithms. Do not duplicate authoritative tokens between TS and SCSS.
- Logical CSS properties (inline/block) for localization and future right-to-left compatibility. Scoped hover/focus states and \`prefers-reduced-motion\`.
- Code-split CSS with route/component boundaries; avoid importing huge styles globally. Ship one icon family as SVG/optimized per-icon components, not multiple libraries.
- Never style authorization via hidden class: backend must enforce access independently.

## 6. BFF, cache and asynchronous events under load

### BFF scaling

**Initial:** stateless Next.js server BFF module as a discrete layer in the deployment; backed by authorized service APIs.  
**When independently necessary:** extract \`apps/studio-bff\` into dedicated TS service with same public API contract and feature boundaries; browser should not need rework.

- BFF owns browser OIDC session, CSRF, trusted workspace mapping, authz, DTO redaction, service adapters, correlation, rate limits and response aggregation; NEVER owns Builder/Evaluation/Release domain authority.
- Server-only service tokens/keys must not appear in Next public variables, HTML, browser bundles, traces, logs, hydration state or client exception payloads.
- For cross-service overview, use bounded parallel reads and per-source timeout/bulkhead/circuit breaker; return **partial-with-staleness** per component, not fabricated zero metrics.
- Prefer cursor pagination with stable \`(timestamp,id)\` (or service-owned opaque cursor), indexed server filters/search; do not download all runs/audit events and filter in browser.
- Tenant-scoped **cache keys contain tenant/workspace ID, resource, version and viewer authorization profile** where applicable. Sensitive per-user views default no-store unless strongly demonstrated safe. CDN only for immutable static assets and explicitly public data.
- Cache invalidation after mutations via acknowledged response + authoritative refetch; never mutate local state into RELEASED.
- Static assets through CDN/compression/long immutable content hashes; BFF horizontal scaling behind ingress; only stateless handlers, no session affinity required with central session store or cryptographically protected session strategy.
- Rate limits by tenant + user + resource + action; protect agent runs, signed uploads, optimization and releases separately. Queue/async long work in backend; HTTP 202 + workflow/job receipt is normal.

### SSE & streaming scale

- SSE is a **projected notification feed**, not a database or direct Kafka subscription. Consumers receive sanitized, authorized events.
- One or a few SSE connections per workspace/page; avoid one EventSource for every visible agent row. Use BFF fanout and scoped stream per workspace / resource filter.
- Use replay cursor/Last-Event-ID, bounded replay retention, heartbeat, reconnection backoff with jitter, and authoritative GET after missed/gapped events.
- BFF event transport must support horizontal replicas (Redis Streams/pubsub + durable replay read model or another managed adapter chosen after ADR). In-memory SSE history per Node process is not sufficient.
- At-least-once events: deduplicate by source event ID/sequence, monotonic revision checks, out-of-order reconcile; no exactly-once UI promises.
- **Connection budgeting:** measure concurrent streams, reconnections, BFF memory per stream and egress bandwidth; autoscale by real load metrics, not an invented single-user-per-container ratio.
- Fallback polling with bounded cadence/jitter; tabs/background pause non-critical refresh; disconnect on logout/tenant switch.
- Never leak cross-tenant events through shared channels, room IDs or wildcard fanout. Verify stream authorization on connect and before replay/delivery where privileges can change.

## 7. Large-scale browser performance and accessibility

- React Server Components/SSR for initial authorized shell and list summaries; Client Components only for interactivity, heavy grids and live inspector.
- Route-level dynamic imports: LangGraph visual inspector, Monaco editor, complex diff engine and charts load only when relevant. Do not preload the operator console for normal customers.
- List virtualization after measured density threshold; use cursor paginated records and stable keys. Long traces should be paginated by span, server-side filtered, not one huge JSON payload.
- Aggregate charts in backend; the browser receives only aggregated permitted data, not 100k raw events.
- Workers for genuinely heavy local deterministic formatting/layout work (if metrics justify), not for moving privileged server validation to the browser.
- Image/icon/font loading: subset local font assets where lawful, use responsive images, minimize JS SVG icon bundle, avoid sending raw PDF bytes to RSC state.
- Performance budgets **proposed targets to validate**, not observed facts:
  - p75 LCP <= 2.5s on agreed test profile and location;
  - p75 INP <= 200ms;
  - p75 CLS <= 0.1;
  - initial route JS compressed budget <= 180 KB **for simple dashboard route, after measurement and excluding necessary platform runtime as documented**;
  - first results lists page size 25–50 records, adjusted based on UX and API capacity;
  - workflow event UI latency p95 <= 3s when stream healthy, target subject to load test.
- Accessibility: WCAG 2.2 AA goal, focus order and keyboard support, semantic tables/timelines, ARIA live updates with throttling, reduced motion, dark-mode contrast, and user-controlled density.

## 8. Quality gates & CI/CD for large teams

### Pull-request checks

1. TypeScript \`tsc --noEmit\` / \`tsc -b\` per package; generated OpenAPI clients verified against pinned sources and breaking-change compatibility report.
2. ESLint (incl. boundaries, rules-of-hooks, no-explicit-any, no unsafe casts, server-only imports and restricted dependencies), Prettier, Stylelint + SCSS nesting/specificity rules.
3. Vitest unit, React Testing Library and MSW contract-driven component tests, Storybook visual regression for common states (empty/loading/error/blocked/success/partial).
4. Playwright browser E2E for two customer roles plus operator (on approved synthetic APIs), accessibility (axe), tenant isolation and deep-link auth.
5. Security: dependency/SBOM, static secrets scan, CSP and auth checks, upload and signed-URL refusal, forbidden state promotion, cross-tenant data/cache/SSE tests.
6. Build-size and performance regression budgets; route chunk analysis and Lighthouse/Web Vitals lab measurements; runtime tracing redacted.
7. Review by appropriate CODEOWNER for design tokens, BFF identity, release controls and shared SDK; changes in a service OpenAPI trigger generated-client compatibility review.

### Caching and deployments

- Turborepo cache only deterministic outputs; remote cache optional. Never cache secrets or raw customer datasets; inspect logs and environment inputs (Turborepo logs themselves are cached artifacts).
- CI \`pnpm --frozen-lockfile\`, pinned Node runtime and package manager major, immutable build artifact with commit SHA, environment-specific server configuration and vulnerability checks.
- Preview environments only with synthetic data and test-only identities. No production credentials, external effects or shared gold vault.
- Stage/canary rollout with feature flags; frontend rollback independent of backend when compatible API version; old UI gracefully handles new status/fields or declares unavailable.
- BFF health probes and dependency readiness: dependency outage is degraded view, not necessarily 500 for every route.
- Instrument error budgets and rollback conditions before broad rollout; define clear incident ownership and safe operational action logs.

## 9. Failure drills / scale tests

| Drill | Expected safe result |
| --- | --- |
| 10k agents / workspace with 100k historical runs | Server pagination, virtualization, no large client arrays, bounded BFF memory |
| 1k users reconnect after network outage | Backoff+jitter, replay cursors, bounded stream fanout, no database thundering herd |
| Registry returns new enum/status | Generated client and runtime parser flag unsupported, UI cannot assume tool approved |
| Evaluation unavailable | Correct per-source unavailable state; never show 0 failures or verified PASS |
| Two tenants request same run ID | Tenant-scoped authorization/cache keys; neither sees other result or existence |
| Role revoked while SSE connected | Stream disconnected or reauthorized per delivery/replay; no data leakage |
| Build/release double-click or browser refresh | Idempotency key preserved, one operation receipt, server authoritative status |
| Partial rollout where new BFF serves old UI | Explicit API version contract and backwards compatibility; safe refusal for unknown fields |
| Tool run says "paid" but no external receipt | UI says **unconfirmed**; release gate refuses required proof |
| 50k audit spans | Load on demand + server-side search; no blocked main thread |
| Budget exhausted mid-optimization | UI reflects terminal authoritative BLOCKED and no speculative auto-resume |
| CDN serves protected response by mistake | Test must catch any caching of user/tenant-only data; protected data set no-store |

These are **test scenarios**, not measured capacities.

## 10. Architecture decision triggers

| Initial approach | Trigger for more complexity | Possible next step |
| --- | --- | --- |
| Next.js-hosted BFF | Stream connection burden or distinct scaling/SLO profile measured | Separate stateless Node/TS Studio BFF |
| Modular monolith frontend | Multiple independent release teams routinely blocked by coordinated rollout | Consider microfrontend boundaries with shared auth/DS contracts |
| Single monorepo | CI critical path / repo fanout becomes measurable bottleneck | Prune builds by dependency graph; split only with verified cost-benefit |
| SSE for browser | Confirmed need for real bidirectional low-latency interactive control | WebSocket for specific feature only, after auth/backpressure design |
| SCSS Modules + CSS vars | Multiple branded tenants need controlled runtime theming | Token-driven tenant theme overrides with validation; not injected arbitrary CSS |
| Tenant-indexed read model | Large tenant cardinality/SLO needs more isolation | Sharding/partitioning of projection store, explicit data ownership |
| Client-generated diagrams | Measured CPU/memory issues on large graphs | Worker layout, graph virtualization, server aggregated graph projections |

**Do not decide microfrontend federation, Kubernetes or separate process-per-feature solely to appear enterprise-scale.**

## 11. Delivery sequence and ownership gates

- **Foundation (must precede broad UI work):** design-token source + SCSS policy, strict TS + package exports, OpenAPI generation pipeline, role-aware BFF, schema-checked status mapping.
- **Read-only MVP:** workflow/agent views, real source flags, event stream projection, paginated run list; no fake stats.
- **Interactive sandbox:** task wizard, sanctioned artifact ingestion, Registry grants, Builder start, runtime execution, Evaluation scorecard.
- **Safe production lifecycle:** GEPARD independent retest, LiteLLM reconciled cost, gated Release/AgentStore and rollback, A2A authorized call; operator diagnostics.
- **Scale hardening:** rate/connection/load/tenancy tests, synthetic 10k agent fixtures, no cross-tenant cache, performance budgets, preview/canary/rollback and independent BFF scaling only when measured.

### Proposed frontend-only acceptance checks

- All source DTOs validated or mapped with documented runtime validation boundary; unknown state never interpreted as PASS/RELEASED.
- Every feature module has a public API and ownership; no banned cross-feature imports or cycles.
- No global CSS leakage from domain components; theme tokens work across light/dark and reduced-motion.
- Two-tenant negative E2E across HTTP, SSE, cache and artifact links; no exposure of private prompts/holdout/keys.
- Large-run traces and 10k-agent synthetic data do not force unbounded browser memory.
- Actions honor idempotency/auth from backend, including double click and slow timeout.
- CI runs app typechecks, lint, unit, contract, browser and perf checks on immutable revision; P0 paths have smoke tests.
- Production readiness still requires complete service integration tests, approved ADR, auth/KMS and operational SLO.

## 12. Canonical references (official docs, checked 2026-10-28)

- Next.js Sass / CSS Modules: https://nextjs.org/docs/app/guides/sass
- Next.js monorepo transpilePackages: https://nextjs.org/docs/app/api-reference/config/next-config-js/transpilePackages
- TypeScript project references and build mode: https://www.typescriptlang.org/docs/handbook/project-references
- Turborepo caching: https://turborepo.dev/docs/crafting-your-repository/caching
- Turborepo remote cache: https://turborepo.dev/docs/core-concepts/remote-caching

The above are guidance for a **proposed** stack, not evidence of installed packages, validated lockfiles or measured performance.
