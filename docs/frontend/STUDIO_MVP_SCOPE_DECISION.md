# ADR proposal — Agent Factory Studio MVP: necessary vs unnecessary

**Status:** recommended **scope decision**, NOT a ratified ADR-0002, NOT a production-ready feature.  
**Date:** 2026-10-28. **Owner approval required.**  
**Replaces as implementation priority:** the aspirational breadth of STUDIO_UX_AND_DELIVERY.md and STUDIO_SCALABILITY_ENGINEERING.md. Those files remain an optional **target catalog**, not a P0 obligation.

## Executive decision

**Build ONE integrated vertical slice first**, not a storefront for all microservices: scoped Business Task Package → Builder/Registry → verified AgentSpec → sandbox Runtime → independently attested Evaluation → bounded GEPARD repair (when relevant) → retest → operator-reviewed version/release → tangible customer artifact and per-run audit. Never show mocked technical readiness as live. First commercial proof is one specialized B2B operation at acceptable cost/quality; expand to the second distinct fixture (certificate verification) to demonstrate configuration reuse rather than RFQ hardcoding.

A customer sees a **product workflow**, NOT a tab for each microservice. A privileged operator can inspect which service generated each event. No UI can bypass server-owned Evaluation or AgentStore states.

### Conditions / scope

Assume first 1–3 enterprise pilots, a small engineering team and an existing Java/Python microservices repository; request and customer volumes are **unknown**. Do not size Kubernetes clusters, SSE brokers or microfrontends based on made-up 10k-agent targets. Security, real effect proof, retention and tenant ACL remain required even at tiny scale.

## 1. Must build for the first useful pilot

| Priority | Business/UI capability | Minimum implementation | Source owner / prerequisite | Acceptance |
| --- | --- | --- | --- | --- |
| P0.1 | Sign-in, tenant, role and operation authorization | One workspace identity/session layer, 3 useful role profiles: customer/operator/approver, per-resource checks | identity+BFF+Control Plane | deny other-tenant HTTP, files, search and exports |
| P0.1 | One task intake from real business files | Objective, input/output contract, XLSX/CSV + required PDF SOP/template as first accepted formats, examples, owner-approved rules, readiness and immutable snapshot. Add DOCX/JSON/OpenAPI readers when a real customer case needs them, while preserving the larger product acceptance contract | Task Intake/Artifacts **missing** | uploaded files parsed with provenance; missing rule blocks build |
| P0.1 | Trusted tool selection and access | approved Registry tool list, required scopes, missing grants; one or two known integrations; no arbitrary MCP installs | Registry → Builder integration **gap** | explain exact denied capability, no silent grants |
| P0.1 | Build + visible status | explicit idempotent build command; state timeline, blocker/action, refresh-safe polling | Control Plane + Builder | customer sees real status, failure and trace ref after refresh |
| P0.1 | Sandbox test and business artifact | task input, allowed sandbox Runtime, generated file/result, run status, tool effects and evidence | Runtime + file storage | artifact is real; model saying “done” is insufficient |
| P0.1 | Independent quality | PASS/FAIL/BLOCKED, required checks, safety veto, run/evidence correlation, dataset provenance without hidden answers | Runtime signed audit → Evaluation; integrated demo exists | forged/no-effect evidence cannot become PASS |
| P0.1 | Candidate and version identity | immutable spec digest, baseline vs candidate, last verified quality, explicit live/sandbox status | AgentStore + Control Plane | no UI-only RELEASED state |
| P0.1 | Minimal audit and operational view | history of commands, timestamps, safe correlation IDs, error reason, run cost when provider supplied it | Orchestrator/Runtime/Eval logs + minimal BFF read model | operator can diagnose failed scenario without five vendor dashboards |
| P0.1 | Core frontend quality | strict TypeScript, SCSS Modules, accessibility, auth/security tests, real vertical Playwright flow | frontend team | no fake data, critical 401/403/409/replay/timeout tests |
| P0.2 | Controlled release/rollback | Manual operator-approved release or safe read-only pilot mode; real rollout must be gated by independent evidence, production credentials and deployment readiness | Control Plane/AgentStore **not E2E proven** | canary/safe rollback only when real infrastructure supports it |
| P0.2 | Bounded improvement status | show why failure occurred, optimizer proposal/retest, real GEPARD backend label vs mock | GEPARD + Eval + Orchestrator; mock optimization currently | cannot claim actual GEPA improvement from deterministic mock |

Pilot must clearly state if sandbox-only. **Do not ship a visible “Publish” action until actual agent provisioning, identity, approval and rollback are confirmed.**

**Product scope note:** existing `docs/product/MVP.md` asks for XLSX, PDF, DOCX, CSV and JSON/API contracts. Narrowing early implementation to the files demanded by the first chosen pilot is a delivery sequence proposal, NOT unilateral deletion of that agreed product acceptance requirement.

## 2. Minimum screens — exactly five primary surfaces

1. **Agents + compact overview**: list, current state, last operation, requires-action; home may initially be this screen, **no separate dashboard**.
2. **Create Agent (guided wizard)**: 3–4 grouped steps instead of forced 5; structured task, files/knowledge, approved integrations and acceptance; assistant suggestions optional.
3. **Agent Details / Mission Control**: business objective, AgentSpec version, status, verified checks, permitted operations, CTA; tabs are sections, not new infrastructure applications.
4. **Workflow & Run Detail**: one timeline component with business and privileged technical expansion; display actual artifacts, calls, denied effects and error instructions. Distinguish build workflow from runtime run using explicit links/IDs.
5. **Quality & Versions**: inside agent detail or one associated screen; baseline/candidate, evidence, failed check, bounded optimize/retest, release approval when supported.

**Operator needs initially one protected diagnostics drawer** (service, trace, correlation, rejected tool, last real event, cost); not eight admin navigation pages. Integrations are step/modal linked from wizard; separate catalog only when >3 connectors and lifecycle/owners justify it.

Customer journeys: create draft → validate READY → request build → watch real status → sandbox run → inspect artifact → independently verify → fix or BLOCKED → authorized operator-approved promotion (where implemented). Mandatory first-use tasks should be achievable without opening technical graph view.

## 3. Frontend stack — what is justified NOW

| Area | NOW | Only when triggered |
| --- | --- | --- |
| Language | TypeScript strict + ESLint; optional high-value `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` | branded IDs and additional TS project references after concrete type collisions/package scale |
| Runtime | ONE Next.js React application with server Route Handlers for BFF, OR Vite SPA + existing authorized backend if infra requires static site. **Prefer Next.js as chosen single deployment when browser OIDC and safe aggregation are needed.** | independent `studio-bff` process when streaming/session/traffic has measurably different scaling profile |
| Styling | SCSS Modules + small CSS variable token theme, native Grid/Flexbox | token codegen / theme package after multi-brand or independent UI consumers |
| Package manager | pnpm with single frontend package; project folders within application | pnpm workspaces if **at least 2 independently reusable packages** appear; Turborepo only after build/CI bottleneck measured |
| UI | one accessible component primitive kit, 15–20 core primitives, icon set | full public component library or Storybook governance once >1 consuming app/team |
| Server data | TanStack Query for browser reads, URL params for filters; server-only transport/auth in BFF | global state management only for demonstrably complex local cross-feature state |
| Schemas | Backend-contract-checked DTO mapping and Zod at external trust boundaries; generate clients after upstream OpenAPI stabilizes | complex multi-language SDK publishing/version matrix |
| Forms | React Hook Form + Zod for wizard | large configurable schema-driven forms if 3+ distinct business task types prove need |
| Async observation | **GET polling 3–5 s only while active workflow page is visible**, with backoff, jitter and ETag/revision support | SSE from BFF when frequent updates or many users justify; one per workspace, not per agent card; Redis/replay only once horizontally scaled streaming is real |
| Charts | none required for pilot. Small accessible tables/metrics first | Recharts for validated time series after real samples and user demand |
| Agent graph | none required for buyer; textual steps and tool pins sufficient | React Flow **read-only** to help debug complex multi-step graphs; editable graph much later |
| Tests | Typecheck + lint + critical Vitest + Playwright E2E with sandbox fixtures and live services; basic accessibility tests | broad Storybook snapshot infrastructure, remote visual platform, large synthetic load fixtures after stable UX |
| Ops | structured server logs + correlation ID, limited diagnostics in Studio | Langfuse full embeds, distributed OTel UI, incident console only after real scale |
| Deployment | one frontend deployment, real backend service boundaries, env-specific server-only config, smoke tests | frontend microfrontends, multiple frontend clusters, independent BFF autoscale only on measured need |

Official documentation confirms Next.js supports SCSS Modules and Route Handlers; neither forces an additional BFF deployment. Do **not** use Next.js solely for SEO for an authenticated-only internal tool; its value here is shared TypeScript/server auth and request aggregation.

## 4. Reclassify previous features without removing the underlying microservice roadmap

| Proposed earlier | Decision | Reason / trigger |
| --- | --- | --- |
| Entire detailed homepage analytics | **CUT for P0** | No production metrics yet; simple agents list/action inbox conveys value |
| Separate Quality Center, model benchmarking pages | **SIMPLIFY** | One baseline/candidate table inside Agent; separate section at many evaluations/customers |
| 7+ navigation sections + 8 Ops panels | **CUT for P0** | Duplicates workflow/run view, high surface maintenance |
| Rich AI Buddy chat with tool-generated actions | **LATER** | Structured task form is reliable; add copilot only after real user friction evidence |
| Visual LangGraph editor / node designer | **NO for P0** | Competes with “agent from business task” promise, creates safety/validation burden |
| React Flow diagram | **LATER, read-only** | No reason to ship graph renderer before having a complex actual graph |
| SSE + Redis Streams + durable projection store | **LATER** | Early active-page polling is enough; broker fanout solves not-yet-measured problem |
| Standalone Studio BFF + separate service auth database | **LATER** | Next Route Handlers are a logical BFF; keep service contracts, avoid deploying an extra service |
| pnpm workspaces + Turborepo + remote cache immediately | **LATER** | One frontend does not need a second task orchestration layer |
| Multiple design token generator packages | **LATER** | One `tokens.scss` / `tokens.css` set and shared mixins sufficient; no duplicate tokens |
| Microfrontends / Module Federation | **REJECT without proven need** | Fragmented auth, versioning, UI quality and heavy cross-team coordination |
| Full Storybook library with screenshot approval on every variant | **LATER** | Start with component tests and a few critical screenshot/visual tests |
| Customer billing / invoices | **LATER** | Monetization/pricing not validated, use provider cost display and human invoicing |
| Soup GPU training UI | **LATER** | Separate opt-in research/training job, not the first buyer journey |
| Pi Durable switch UI | **REJECT for MVP** | Chosen Runtime is Python LangGraph/PostgreSQL; Pi is research |
| Two-company A2A canvas | **LATER** | Optional add-on, not needed for one-company product |
| Agent marketplace / plugin installation UI | **LATER** | First prove one approved integration; avoid untrusted supply chain |
| Auto-optimize button with unsupported backend | **REJECT until real** | Need real DSPy/GEPA; if using mock label it clearly in isolated synthetic demo |
| Auto-production release | **NOT IN FIRST PILOT** | Release evidence/approvals and deployment proof not yet integrated; manual/policy-gated path later |
| Separate operator console with 15 pages | **LATER** | One protected inspector plus logs/backlinks first |
| Huge dashboards / live flamegraphs for every run | **LATER** | Debug links to existing observability tools and bounded safe trace previews first |
| SSR optimization, CDN, sharding, Kubernetes and fine-grained microfrontend deploy | **NO ADVANCE WORK** | Use when observed bottleneck warrants complexity |

**Do not confuse UI deferral with removal of business-invariant support:** security tests, separate hidden holdout, idempotency, risk policy and immutable evidence are **mandatory** from the first real pilot. Keeping a service hidden in UI while implementing required backend capability is valid.

## 5. Critical backend blockers that outrank UI ornament

1. **Task Intake + artifact ingestion**: no verified live ingestion API/snapshot handling; build wizard currently only a proposed contract.
2. **Registry → Builder**: temporary manifest projection and unresolved operation/version-pin authority.
3. **Runtime → Evaluation**: isolated Ed25519 cross-service test exists; production key management, durable audit and real external effect receipts remain unproven.
4. **Evaluation → Orchestrator/AgentStore**: real independent evidence contract, release authorization, deployment and rollback E2E pending.
5. **LiteLLM Gateway**: owner-selected MVP dependency; persisted per-tenant budgets/keys/usage must work before paid operation.
6. **Runtime provisioning + A2A auth**: production AgentSpec/version deployment and controlled callers unverified.
7. **Real GEPARD**: deterministic test patch is not GEPA optimization. Must verify actual optimizer before a customer-facing “improved automatically” claim.
8. **Identity, secrets, tenant security, retention and business approval**: cannot outsource to CSS/buttons.

**Therefore:** implement a useful read-only workflow view first if needed, but never call the factory a functioning self-service SaaS until backend vertical-slice gates pass.

## 6. Minimum quality/scale gates

- Every backend-derived status, approval and business output stays server-owned; UI never optimistic-promotes into RELEASED/PASSED.
- Two tenant isolation tests covering UI HTTP, files and cache; 403/409 failures handled, no silent exposure.
- Real workflow update on refresh and across browser navigation; idempotent start/retry; safe blocked reasons.
- Unauthorized tool, contaminated hidden holdout, missing verified external effect and forged audit never show “success.”
- Successful synthetic two-case smoke across same Builder implementation before calling product configurable.
- Per-route request budgets and bounded response payload; paginated run list and lazy traces when actually needed.
- Publish quantitative performance budgets only after a baseline device and workload profile has been measured; do not assert “10k agents” capacity based on code architecture alone.
- UI deployment rollback works and unknown API statuses fail safely.

## 7. Simple implementation layout

~~~text
apps/
  studio/
    app/
      (auth)/
      w/[workspaceId]/
        agents/
        agents/new/
        agents/[agentId]/
        workflows/[workflowId]/
        runs/[runId]/
      api/studio/          # Route Handlers = first BFF
    src/
      features/
        agent-creation/
        agent-overview/
        workflow-timeline/
        run-detail/
        quality-version/
      server/
        auth/
        adapters/         # CP / Registry / Runtime / Eval / Store
        projections/      # safe client view models
      shared/
        ui/
        styles/           # tokens.css, globals.scss, components/*.module.scss
        lib/
        contracts/
    package.json
    tsconfig.json
    next.config.ts
~~~

Keep backend Java/Python directories unchanged. Split packages only when actual duplication / independent consumers appear. Use server-only modules for tokens/secrets. A modular monolith frontend is fully compatible with microservice backends.

## 8. Ordered milestones, with go / no-go

| Milestone | Delivers | Hard go/no-go |
| --- | --- | --- |
| M0 | Task/Agent/Workflow IDs, auth ownership, minimal DTO shape and blockers ratified | no unresolved P0 ownership ambiguities; ADR-0002 ratification still required for final topology |
| M1 | Agents list + workflow timeline + operator diagnostic drawer with real CP statuses | 401/403, stale/blocked, refresh/reconnect tests, no fake data |
| M2 | Task wizard + artifact upload + Registry selection + Builder command | real snapshot ready, exact scope and validation, same generic UI handles RFQ and certificate task |
| M3 | Sandbox run + downloadable real artifact + signed independent Evaluation scorecard | forged/no-effect evidence blocked, holdout isolated |
| M4 | GEPARD real bounded candidate+retest, persisted model spend via LiteLLM, operator-reviewed release/rollback | baseline and independent improvement; release proof E2E and canary successful |
| M5 | Production monitoring/A2A and only then richer dashboard, SSE and provider cost analytics | real load/usage/alerting measured, verified customer task outcome |

**Commercial MVP** = M0–M4 with the explicit safe pilot deployment mode; M1–M3 are useful working prototype milestones, not equivalent to “all features ready”.

## 9. Revisit triggers

Adopt **SSE** if users need near-instant dozens of updates per minute or polling creates measured load/staleness. Use durable replay fanout only with multiple BFF replicas and large stream counts. If HTTP/1.1, multiple EventSource tabs can exhaust browser per-origin limits; ensure one scope connection.

Adopt **Turborepo** if frontend grows to 3+ meaningful build tasks/packages and CI repeatedly rebuilds unchanged outputs; start with pnpm scripts now.

Adopt **separate BFF** if measurable CPU/stream concurrency, independent security/compliance ownership or release cadence require separate deployment. Keep adapters modular so extraction is possible.

Adopt **React Flow** only once a pilot operator cannot diagnose agent behavior from a textual timeline and request/response evidence.

Adopt **full billing** after a tested price model, actual invoices and reconciled usage; not simply because a Stripe SDK exists.

## 10. Risks of under-building vs over-building

**Under-build:** skipping tenant isolation, evidence verification, file provenance, approvals and idempotency results in a false/unsafe B2B product. These cannot be postponed.

**Over-build:** adding a separate TS gateway service, Redis streams, a graph IDE, billing, microfrontends and marketplace before one independently verified business result produces more software to support without proving a customer will pay.

The correct cost center is the **quality of the underlying vertical slice and its transparency**, not the number of UI features or sophistication of engineering logos.

### External implementation references (checked 2026-10-28)

- Next.js Sass Modules: https://nextjs.org/docs/app/guides/sass
- Next.js Route Handlers: https://nextjs.org/docs/app/getting-started/route-handlers
- Turborepo build caching: https://turborepo.dev/docs/crafting-your-repository/caching
- EventSource SSE limits: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
