# Agent Factory Studio — boxed product features and truthful UI exposure

**Date:** 2026-10-28. **Status:** owner-requested target scope, not proof of implementation; ADR-0002 still pending formal owner decision.

## 0. Product interpretation

“Box” means **the assembled product's feature set / modules**, NOT a commitment to on-prem/private deployment or a claim that every backend component is production-ready. Separate four axes:

1. **Included in target product**: CORE, OPERATOR, ADVANCED, LAB, NOT_INCLUDED.
2. **Delivery priority**: NOW / NEXT / LATER / RESEARCH; NEXT/LATER can be *committed target capabilities*, not a suggestion to drop them.
3. **Engineering evidence**: DESIGNED_ONLY / COMPONENT_TESTED / SYNTHETIC_INTEGRATION_TESTED / REAL_STAGING_TESTED / PRODUCTION_VERIFIED; this must be based on immutable SHA + CI/log evidence, not PR prose.
4. **Tenant availability**: HIDDEN / PREVIEW_ONLY / DISABLED_WITH_REASON / ENABLED; computed server-side from entitlement + authenticated actor permissions + environment + dependencies + actual deployed capability health, not hardcoded frontend flags.

A module can be product-committed and still HIDDEN/DISABLED until ready. Never equate design, code presence, an HTTP 200, GitHub green SDD, or a passing isolated synthetic gate with production readiness.

## 1. Owner-updated scope decisions (supersedes P0 cut recommendations)

**Decided for target Agent Factory Studio:**
- **Full Operator Console with 15 dedicated operational modules is mandatory product scope.** Its navigation/permissions/DTOs should be designed NOW. Backend-backed functionality must roll out incrementally and truthfully; no fake KPI charts or active destructive controls.
- **Large shared chart library is mandatory** for Business Analytics and Operator Console, with domain-owned data and explicit chart definitions. A centralized typed chart kit is preferable to several unrelated plotting packages.
- **Two-corporation collaborative agent builder is committed strategic functionality**, designed now as a first-class advanced flow: two isolated tenant-owned BTPs and AgentSpecs, independent approvals and runs, shared authorized A2A interaction and individual + joint Evaluation. It is not a prerequisite to sell the single-agent starter pilot; user decision to make it first-wave would require extending separate bilateral backend scope.
- **Visual LangGraph editor is explicitly added to idea backlog; no implementation yet.** Read-only graph inspector can precede editing. Future editing compiles through validated graph→AgentSpec with immutable revision and independent gates; no direct production graph modification.
- **Microfrontends are explicitly added as an architectural option/idea, not implemented.** Start with modular React/Next, keep route/module boundaries extractable; only adopt independently deployed frontends if organizational or operational evidence justifies it.

**Not decided:** a single deployment vs private customer “boxed” installation, licensing tiers/pricing, whether 2-company collaboration must be ready before first external pilot, and physical microservice topology. Do not invent approval of these matters.

## 2. Product package / user-visible module matrix

| Module & UI | Target box | Delivery | Backend owner/data authority | What is user-visible when implemented | Current status/evidence |
| --- | --- | --- | --- | --- | --- |
| Business Task Intake | CORE | NOW | Task Intake + Artifact Ingestion | Structured business brief, uploaded files, revisions and READY snapshot | **DESIGNED_ONLY**; intake/upload service not live |
| Trusted Tool & MCP selection | CORE | NOW | Registry + Builder | Approved connectors, why selected, required scopes, typed blockers | Java component tests / incomplete live Builder adapter |
| Agent Builder | CORE | NOW | Builder + Orchestrator | Immutable AgentSpec, steps, selected tools, build progress | Component tests; no customer-ready end-to-end |
| Sandbox Agent Runtime | CORE | NOW | Python LangGraph Runtime | Trial runs, output artifacts, permitted tool operations | Isolated component tests; production provisioning and customer IAM open |
| Business Evaluation | CORE | NOW | Independent Evaluation | PASS/FAIL/BLOCKED, evidence, failed requirements | Synthetic signed Runtime↔Evaluation E2E **tested**; full live not verified |
| Limited GEPARD optimization | CORE | NEXT | GEPARD + Orchestrator/Evaluation | Candidate diff, baseline/retest comparison | Deterministic test optimizer only; real GEPA unproven |
| LiteLLM model routing | CORE | NOW | Model gateway | Model policy/limits and real billed usage | Adapter/proposal; persisted tenant budget/production provider usage open |
| Versioning, release, rollback | CORE | NEXT | AgentStore + Control Plane | Current pinned version, approvals, release/rollback state | Java workstream code/tests; true cross-service release E2E open |
| Basic A2A endpoint and caller access | CORE | NEXT | Runtime + A2A ingress | Agent Card, allowed caller, task history | Isolated SDK/runtime work; production IAM/ingress open |
| Basic security + observability | CORE | NOW | IAM, Runtime, Orchestrator, telemetry | Safe operator events, status, incident info | Partial structured logs and component audit only |
| **Full 15-section Operator Console** | **OPERATOR (MANDATORY)** | NOW design + staged wiring | All services via privileged BFF | Fleet, jobs, artifacts, security, traces, tools, metrics, release controls | **DESIGNED_ONLY** as unified UI; underlying services at mixed readiness |
| **Shared chart library + analytic views** | **CORE + OPERATOR (MANDATORY)** | NOW foundation + incremental charts | Source-specific verified time series/counters | Certified charts only when underlying real series exist | **DESIGNED_ONLY** as UI library; telemetry completeness unknown |
| **Two-company agent construction** | **ADVANCED (COMMITTED)** | NEXT / strategic | 2 BTP/Builder/Runtime instances + bilateral Eval/Orchestrator | A/B joint canvas, independent permissions, shared A2A timeline, partner release matrix | Architecture RFC only; no bilateral deployed proof |
| **Visual LangGraph editor** | **LAB / IDEA** | LATER, not now | Future graph validator/compiler + Builder/Runtime | Edit proposed graph, test, approve new immutable version | **IDEA_ONLY**; deliberately no implementation |
| **Microfrontends** | **ARCHITECTURE OPTION / IDEA** | LATER, not now | Shell/BFF/DevOps | No customer-facing product promise; independent UI releases when justified | **IDEA_ONLY**; deliberately no implementation |
| Optional Soup specialized training | LAB | LATER | Orchestrator→Soup→independent Evaluation | Licensed training job, costs and required approvals | Proposed/optional backend, not a first-pilot commitment |
| Pi Durable alternative | RESEARCH | LATER | Research harness | Engineering benchmark only, never promised as chosen runtime | Python LangGraph is selected MVP; Pi is R&D |
| Billing/marketplace | NOT_INCLUDED first pilot | LATER/after commercial proof | New commerce/partner products | Invoices/marketplace only once legally/commercially ready | Not implemented |

**Evidence caveat:** several component test results are documented by service teams but not independently rerun on the current integration head. The 2026-10-27 isolated Runtime/Quality GitHub test had 3 passing Python E2E tests, including missing external receipt rejection. It is not a production A2A or release proof.

## 3. Exactly 15 required Operator Console sections

These are **mandatory target UX modules**, not fifteen independently deployed frontend apps and not a claim of 15 operational APIs already live.

| # | Section (route suggestion) | Source & objects | Must support in mature box | Pilot wiring / truthful empty state |
| --- | --- | --- | --- | --- |
| 1 | **Platform Fleet** `/ops/fleet` | Railway/deployment provider, container health, service registry | Instances, regions, versions, restarts, readiness, capacity | Actual provider snapshot; no fake SLA |
| 2 | **Workflows & Queues** `/ops/workflows` | Control Plane state, command outbox, event inbox, Kafka/DLQ | Workflow timeline, attempts, stuck jobs, idempotent safe replay | CP status/audit where real; Kafka lag unavailable if broker absent |
| 3 | **Builder / AgentSpecs** `/ops/builder` | Builder, immutable AgentSpec store | Builds, selected tools, graph and prompt diffs, rejected specs | Read-only when source not live |
| 4 | **Runtimes & Checkpoints** `/ops/runtime` | LangGraph Runtime, PG checkpoints, effect ledger | Threads, restart/recovery, safe step diagnostics, runs | Cannot claim production durability based on isolated test DB |
| 5 | **Tool/MCP Registry** `/ops/registry` | Java Registry | Manifests, version, provenance, maker-checker, revoke, scope blockers | Real registry API only after IAM/persistence acceptance |
| 6 | **Connectors & Secrets** `/ops/connectors` | Vault/integration owner + Registry | Connector health, grants, credentials lifecycle, sandbox tests | Never display raw keys/tokens |
| 7 | **Task Intake & Artifacts** `/ops/artifacts` | BTP/artifact ingestion | Parse failures, file provenance, unsupported formats, retention | Source currently not deployed; clear blocked state |
| 8 | **Evaluation & Holdouts** `/ops/evaluation` | Independent Eval | Jobs, dataset versions, signatures, blocked cases, leases | No gold answer exposure; synthetic vs real prominently labeled |
| 9 | **GEPARD Experiments** `/ops/gepard` | Optimizer/evaluator | Candidate diffs, tuning inputs, budgets, independent retests | Mock is labeled MOCK; cannot show fabricated GEPA gains |
| 10 | **Models & LiteLLM** `/ops/models` | LiteLLM + reconciled spend | Provider health, model routes, tokens, spend, quota, fallbacks | Cost unknown if no trusted usage |
| 11 | **A2A & Bilateral Lab** `/ops/a2a` | Agent A/B Runtime, A2A adapter, bilateral Eval | Agent Cards, protocol history, A/B paired experiments and approvals | Bilateral feature planned; sandbox simulation labeled |
| 12 | **Releases & AgentStore** `/ops/releases` | Orchestrator, AgentStore, deploy controller | Candidate/verified/released versions, approvals, rollback history | No publish unless real independent evidence and deployment |
| 13 | **Traces, Logs & Metrics** `/ops/observability` | OTel/Langfuse, service metrics | Run correlation, traces, structured logs, service error cause | Redact input/prompts/holdout/PII; show ingestion gaps |
| 14 | **Security, Tenants & Audit** `/ops/security` | Identity/policy/registry audit | Scoped roles, signer/key status, access anomaly, immutable logs | Tenant-separated and privilege-gated |
| 15 | **Incidents, Alerts & SLO** `/ops/incidents` | Metric/alert source, incident state | Alerts, acknowledgments, customer impact, operator runbooks | No mock open incidents, percentages or uptime |

Each section must have real empty/loading/unavailable/blocked/error states and exact permitted operator actions. The owner does not authorize a mutation by merely displaying a button. Each operator command needs role + scope, reason, confirmation, audit and idempotency. **High-risk actions** (revoke, release, rollback, key rotation, retry irreversible effects) may have specialized approval steps.

## 4. Full chart library as a shared, typed product capability

**Chosen core candidate:** Apache ECharts + TypeScript adapter in `features/analytics` / `shared/charts` or a future package when multiple apps exist; SCSS Modules/theme tokens; dynamic import and tree-shake per chart type. Do not include three overlapping chart engines without evidence. ECharts supports a broad chart family and SVG/Canvas modes, with dataset separation and progressive rendering; validate bundle weight/perf before choosing imports.

### Chart templates to include in product design

| Visualization | Why it exists | Backend source / trusted denominator |
| --- | --- | --- |
| 1 Line/area trend | Verified run success / failures by date | Evaluation+Runtime confirmed outcome, timeseries interval |
| 2 Stacked bar | Spend/tokens by model/agent | LiteLLM usage and reconciled model routes |
| 3 Horizontal bar | Top failure codes | Evaluation/Runtime safe taxonomy |
| 4 Scatter / bubble | Quality-vs-cost candidate benchmark | independent Evaluation and billed cost per success |
| 5 Heatmap | Case failure/regression across versions | safe aggregate Evaluation, never hidden gold |
| 6 Funnel | Intake→Ready→Build→Eval→Released conversion | source-stage counts with exact period and denominator |
| 7 Timeline/Gantt | Job/step latencies and waiting states | Orchestrator event timestamps and trace spans |
| 8 Waterfall/flame chart | Per-run latency breakdown (operator) | verified OTel/Langfuse spans, server-side redaction |
| 9 Sankey | Model/tool routing/cost distribution (operator) | authenticated gateway and runtime invocation edges |
| 10 Treemap | Cost by tenant/project/agent under proper ACL | reconciled usage, no cross-tenant disclosure |
| 11 Histogram / boxplot | Latency/retry distributions | bounded real run samples |
| 12 Gauge/progress | Budget usage vs limits | persisted authoritative budget |
| 13 Dependency graph | Service/connector incidents and blast radius | observed service topology/health |
| 14 Donut/pie | Status composition for small bounded categories | authoritative records, avoid large categorical sets |
| 15 A2A swimlanes / sequence | Bilateral message and approval chronology | signed, disclosure-filtered A2A event log |

The library is a **real scope item**, but each chart has a capability gate: no source/denominator = unavailable with explanation; no invented placeholders, fake trend, equal-weight averaging or missing-data-as-zero. A table/CSV export and accessible textual summary must accompany critical metrics; charts are not the audit source.

### Chart contract

`ChartDefinition {chart_id, type, query_key, source_refs, schema_version, time_range, granularity, series, units, baseline_ref?, sample_count?, complete, last_observed_at, redaction_level}`.

Every chart includes unit, source, timeframe, sample count, empty/partial/error, timezone/currency and navigation to underlying approved evidence; chart data is aggregated/paginated server-side and tenant scoped. Do not send raw high-cardinality OpenTelemetry spans to browser to compute graphs. For very dense operator charts use progressive rendering and data windowing; benchmark actual browser memory and JS.

## 5. Twin-corporate collaborative builder — product feature definition

**Mode switch in Studio agent creation:**
- **Single Agent:** first-pilot path, one BTP and one verified independent release.
- **Two-company A2A Scenario:** Advanced product module, **designed now**, execution only once true backend supported; consent of both companies required.

### Target UX with privacy partition

```text
Tenant A / Buyer Workspace        Shared authorized scenario       Tenant B / Supplier Workspace
──────────────────────────        ──────────────────────────       ──────────────────────────
BusinessTaskPackage A             Shared business objective        BusinessTaskPackage B
A: files, rules, grants           disclosed A2A interface         B: private files, rules, grants
Builder A → AgentSpec A0          scenario contract + budgets     Builder B → AgentSpec B0
Runtime A in sandbox       ←── authenticated A2A ──→      Runtime B in sandbox
Private Evaluation A              Joint result / public receipt   Private Evaluation B
GEPARD A → candidate A1           A0×B0 / A1×B0 / A0×B1          GEPARD B → candidate B1
Independent Release A             A1×B1 cross-play                Independent Release B
```

### User journey / data requirements
1. Organizer creates consent-bound bilateral scenario or invites a second authorized workspace; invitation conveys only minimal public summary.
2. Each company independently enters BTP and grants a sealed selection of information. No partner view of private prompt, system instructions, catalog pricing, secrets, memory or holdout.
3. Each gets an independently compiled and pinned AgentSpec from the same Builder system, separate runtime containers and dataset ACL.
4. Shared sandbox A2A dialogue shows only disclosed messages/artifacts/claims and per-party statuses. Underlying private tool traces remain visible only to authorized owner.
5. Evaluation assesses **A independently, B independently, and jointly**. A shared PASS cannot override failure on either party's safety/contract requirements.
6. GEPARD proposes separately for A and B; test `A1×B0`, `A0×B1`, `A1×B1`, with pinned prior baselines and held-out scenarios. Never force one party to accept the other's candidate.
7. Two distinct release decisions; a joint protocol-breaking rollout requires consent of both sides. Each side can rollback independently with compatibility check.
8. Dashboard reports joint verified completion, messages/latency/cost, privacy/safety, protocol errors, per-party verified value; no raw sensitive counterparty details.

### Dependencies / acceptance

- BilateralScenario immutable revision, A/B tenant-scoped BTPs and separate principal IDs.
- Invitations, bilateral consent and disclosure policy, expiring shared authorization and revocation.
- A2A official SDK interoperability and verified public artifact schema, not private instructions.
- Disjoint private gold datasets, independent A/B + joint evaluation signed evidence; no holdout leak.
- Runtime A/B tenant/isolation tests (incl. memory, tools, secrets, logs, cache, artifact signed URLs and SSE).
- Orchestrator commands two builds and sandbox Eval; no magic Kafka self-orchestration.
- Clear automated failure handling if one organization withdraws consent, revokes tool, changes AgentSpec or is offline.
- Owner-controlled release gate per tenant and compatibility rollback.
- First acceptance may use **two synthetic tenants**, but production availability is NOT unlocked without real IAM/consent and deployed cross-service E2E.

## 6. Visual LangGraph editor — recorded IDEA, not implementation

- **Status: IDEA_ONLY**. Suggested implementation later: React Flow (xyflow) for graph canvas + schema-driven node registry, controls and type validation; never expose direct source-code editing or untrusted arbitrary Python functions through a UI.
- Use versioned graph IR with typed nodes `Start, LLM, ToolCall, Decision, Approval, Memory, Retrieve, A2ASend, A2AReceive, End`, plus typed edges and typed input/output schema.
- Read-only inspector first: active node, checked permissions, tool version, trace and checkpoint.
- Editing (future): drag/drop, inspect schemas, validate allowed connection, cycles, bounded loops, sandbox run, graph diff/rollback, save as a **new immutable candidate AgentSpec**.
- Every changed tool/graph/memory permission or consequential effect must pass Registry authorization and independent Evaluation; only Orchestrator may release. No direct rewrite of live LangGraph state or production runtime nodes.
- No work scheduled now; no mocked editor claiming real save/run functionality.

## 7. Microfrontends — recorded architecture IDEA, not implementation

- **Status: IDEA_ONLY**; first implementation remains a modular TypeScript + React/Next.js frontend, SCSS Modules/design tokens, shared typed contracts and BFF.
- Extraction candidates (only if measured): `Customer Studio`, `Operator Console`, `Analytics / Charts`, `Bilateral A2A Lab`. All share identity/roles and UI design system via versioned contracts; no cross-application direct database calls.
- Evaluate **route-based composition** vs Module Federation **when** multiple independent teams require separate deployment timelines; avoid assuming Module Federation works identically across Next.js App Router/SSR and host environments.
- Technical guardrails before adoption: single sign-in, tenant-scoped BFF API, independent route ownership, compatible design tokens and React runtime versions, CSP/asset integrity, error boundaries, shared navigation, release version matrix and rollback.
- Hard trigger: independent frontend deployment/release ownership with measurable coordinated-release bottleneck, or different SLO/availability and sustained parallel team work. Multiple backend microservices alone do **NOT** justify microfrontends.

## 8. Reality table / delivery program

| Phase | Engineering deliverable | Frontend treatment |
| --- | --- | --- |
| **F0 now** | Full Studio IA and 15 Ops modules defined; chart taxonomy and typed chart contract; A/B scenario UX and schema RFC; LangGraph editor and MFE idea contracts | Screens can be designed for all, **no claim any unimplemented action works** |
| **F1 live read-only** | Session + BFF; agents/workflows/real statuses, Ops Fleet/Workflows/Traces where live, chart kit with grounded series, evidence-safe run inspector | Enable data-backed surfaces only |
| **F2 single-agent pilot** | BTP artifact upload; Registry/Builder; real sandbox Runtime; verified Evaluation; first real GEPARD; controlled release and actual LiteLLM budgets | Enable self-service creation and pilot operations, expand Ops detail |
| **F3 advanced bilateral** | Consent + two independent builds/runtimes + A2A joint eval + cross-play + separate release | Enable dual-agent builder only after real bilateral E2E |
| **F4 later** | Visual graph editing and/or MFE extraction on justified roadmap | Never treated as first-pilot blocker |

**Operator Console and chart library are now required product scope** even though not every Ops panel or chart is scheduled for first working pilot. "Mandatory" means ownership in target features, documented IA/contracts and planned backend wiring/acceptance, NOT fabricated real telemetry.

## 9. Capability-gated BFF contract (PROPOSED)

Public client receives a **sanitized server projection**, e.g.:

```json
{
  "capability_id": "bilateral.builder",
  "included_in_box": true,
  "package": "ADVANCED",
  "delivery_priority": "NEXT",
  "engineering_evidence": "DESIGNED_ONLY",
  "tenant_availability": "DISABLED_WITH_REASON",
  "reason_code": "BILATERAL_E2E_NOT_VERIFIED",
  "environment": "SANDBOX",
  "allowed_actions": [],
  "last_verified_at": null
}
```

These statuses are **illustrative**. Do not publish this source-control document as live readiness API. The BFF must derive real availability from provisioned services, health/release manifest, IAM scopes, tenant grants, environment and authoritative evidence; an engineer cannot set `PRODUCTION_VERIFIED` only by editing a JSON file.

**Every page has these states:** no access / planned / disabled pending dependencies / unavailable (degraded) / pilot / production / loading / empty / error. Planned features may appear in an explicitly labelled roadmap/info panel and in design reviews; customer production navigation should not show clickable inert actions.

## 10. Documents and conflict resolution

- `STUDIO_MVP_SCOPE_DECISION.md` remains the **minimum first working pilot slice** (not a veto on target Operator Console/chart/bilateral features). Its earlier literal “CUT” decisions for large Ops/analytics/twin builder are superseded by this owner update. P0 delivery of those features still needs source APIs.
- `STUDIO_UX_AND_DELIVERY.md` and `STUDIO_SCALABILITY_ENGINEERING.md` are complete design/scale catalogs; the feature commitment/priority matrix in this document controls revised product roadmap.
- `docs/product/MVP.md` retains single-agent primary first acceptance; dual-enterprise A2A is a committed advanced feature in the larger product and does not silently replace core pilot acceptance.
- `ADR-0002` still needs the owner's own GitHub ratification for physical topology and deployment/security decisions.

**No actual code implementation of graph editor, microfrontends, chart library, Operator Console, or bilateral builder is claimed by this document.**