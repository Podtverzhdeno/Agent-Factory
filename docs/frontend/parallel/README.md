# Parallel frontend implementation: agent work assignment pack

**Status:** PROPOSED TASK PACK; all implementation items OPEN. Source of truth: openspec/changes/studio-cjm-parallel (requirements and tasks).  
**Existing ownership:** docs/parallel/CONTRACTS_V0.md covers original five Java/Python backend workstreams and is READ-ONLY. These ten proposed frontend workstreams do NOT supersede backend ownership. ADR-0002 remains pending owner ratification.

## 1. Dispatch and hard rules

**Exactly 10 autonomous frontend coding agents (A01–A10) + 1 human/lead Integrator (I00).** Any number up to 10 can work concurrently after a COMMON FOUNDATION COMMIT has been frozen. Do not run against ten arbitrary changing heads. The integrator owns all global paths and integration E2E.

- Before code: read AGENTS.md, README.md, .specify/memory/constitution.md, docs/process/SDD.md, this pack, openspec/changes/studio-cjm-parallel/**, CJM_IMPLEMENTATION_BLUEPRINT.md, CJM_UI_CONTRACTS_AND_E2E.md, STUDIO_BOXED_PRODUCT_FEATURES.md and your Axx file.
- **C0 prerequisite (I00):** freeze baseline SHA, one app skeleton, strict TS, SCSS Modules, Next route group layouts, common exports and response error envelope; type-checked fixture clients; agree on DTO and design tokens; do not claim ADR approval.
- **One branch per agent** from C0: frontend/a01-platform, frontend/a02-design-charts, ..., frontend/a10-bilateral. One Draft PR per branch, target C0 integration branch, no merge to main. The existing Studio RFC PR #7 remains a design/spec PR, not the code integration base until integrator explicitly chooses.
- All agents can design/spec their own modules before C0. **No shared code implementation until contract fixture and root skeleton are available.** This avoids parallel assumptions that cannot compile.
- Each agent may ONLY create/change owned directories listed below. If blocked by an absent dependency, create typed adapter fixtures/stubs **inside owned feature folder**, report the connector request; never change another owner's path.
- Root package manifests/lockfiles, Next config, tsconfig, root layouts/provider/global nav, GitHub workflows, OpenSpec canonical specs, shared API DTOs and integration tests belong to I00 unless explicitly delegated in a separately scoped PR.
- All agents use same scoped identities, cache/tenant semantics and exact source-owned statuses in canonical contract. Browser never directly calls internal services or asserts VERIFIED/RELEASED. Synthetic UI fixtures ALWAYS carry a DEMO/TEST provenance marker and never appear as live.
- No feature agent may modify Backend Java/Python service code or docs/parallel/CONTRACTS_V0.md. Service-level bugs are submitted as CONTRACT_CHANGE_REQUEST in its own folder and routed to owning backend agent.
- No agent may bypass security, use external customer data, weaken negative cases or perform live money/ERP effects.
- CODEOWNERS are I00-managed. Branch rebases onto C0 after explicit integrator approval only; do not force push others' branches or merge to main.

## 2. Exact parallel file ownership matrix (glob ownership exclusive)

| Agent | Responsibilities | Exclusive write allowlist |
| --- | --- | --- |
| **A01** | Studio shell/auth/BFF/read models/capability/protocol clients | apps/studio/src/server/**; apps/studio/src/shared/api/**; apps/studio/src/shared/auth/**; apps/studio/src/shared/capabilities/**; apps/studio/src/app-shell/**; apps/studio/app/api/studio/**; apps/studio/app/(auth)/**; apps/studio/src/features/platform/** |
| **A02** | UI foundation, SCSS styles, **shared 15-chart library** | apps/studio/src/shared/ui/**; apps/studio/src/shared/styles/**; apps/studio/src/shared/charts/**; apps/studio/src/features/chart-showcase/** |
| **A03** | BTP wizard, upload/provenance, integration grants, validation | apps/studio/src/features/task-intake/**; apps/studio/app/[locale]/w/[workspaceId]/agents/new/**; apps/studio/app/[locale]/w/[workspaceId]/tasks/** |
| **A04** | agents catalogue, Mission Control, workflow timeline/blocked actions | apps/studio/src/features/agents/**; apps/studio/src/features/workflows/**; apps/studio/app/[locale]/w/[workspaceId]/agents/page.tsx; apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/overview/**; apps/studio/app/[locale]/w/[workspaceId]/workflows/** |
| **A05** | Sandbox playground, real artifact preview, runs and effect receipts | apps/studio/src/features/runs/**; apps/studio/src/features/playground/**; apps/studio/app/[locale]/w/[workspaceId]/runs/**; apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/playground/** |
| **A06** | independent Evaluation, GEPARD candidate/retest, AgentStore versions/release approval | apps/studio/src/features/quality/**; apps/studio/src/features/gepard/**; apps/studio/src/features/versions/**; apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/quality/**; apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/versions/**; apps/studio/app/[locale]/w/[workspaceId]/releases/** |
| **A07** | **Ops #1–5** Fleet, Workflows, Builder, Runtime, Registry | apps/studio/src/features/ops/core/**; apps/studio/app/[locale]/ops/{fleet,workflows,builder,runtime,registry}/** |
| **A08** | **Ops #6–10** Connectors, Artifacts, Evaluation, GEPARD, Models | apps/studio/src/features/ops/pipelines/**; apps/studio/app/[locale]/ops/{connectors,artifacts,evaluation,gepard,models}/** |
| **A09** | **Ops #11–15** A2A, Releases, Observability, Security, Incidents | apps/studio/src/features/ops/trust/**; apps/studio/app/[locale]/ops/{a2a,releases,observability,security,incidents}/** |
| **A10** | bilateral A/B shared creation, consent and cross-play UI | apps/studio/src/features/bilateral/**; apps/studio/app/[locale]/w/[workspaceId]/scenarios/** |

**IMPORTANT:** braces in this document denote the explicit five named folders, not permission to edit parent directory index/layout. Any test files must be **colocated inside the owned feature folders**, not global tests/e2e. Avoid editing adjacent parent route layout.tsx or error.tsx owned by I00. A04 owns only agents/page.tsx under common agents route, not the whole agents parent. All generic navigations, top-level page wrappers, layout.tsx and cross-domain composition belong to I00.

**I00 exclusive:** apps/studio/package.json + pnpm-lock.yaml; apps/studio/tsconfig.json; apps/studio/next.config.*; apps/studio/app/layout.tsx and [locale]/**/layout.tsx; apps/studio/app/[locale]/w/[workspaceId]/page.tsx; apps/studio/app/[locale]/ops/page.tsx; global routing/nav registry, build/test tooling; docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md; openspec/changes/studio-cjm-parallel/**; tests/studio-e2e/**; shared generated OpenAPI status schemas; integration PR and main merge process. Any additional shared base files not explicitly assigned are I00-owned by default.

## 3. Shared architecture/ports for all agent modules

All features import ONLY stable **public exports** from shared libraries, provided by C0:

~~~text
@studio/api         # typed BFF client, retryable error, auth-bound actions
@studio/contracts   # read models, capabilities, paging & source stamps
@studio/ui          # Button, FormField, Status, PageState, DataTable, Dialog, ...
@studio/charts      # ChartView + type-safe chart query, table fallback
@studio/auth        # presentation-only canView/canRequest; never security authority
~~~

The above aliases are **proposed contract names**. Integrator must actually publish aliases at C0. No agent may add its own inconsistent aliases or duplicate global types. If a component needs unavailable upstream field, map to explicit UNAVAILABLE/UNKNOWN (don't fill with fake value) and submit change request.

A01 owns public transport implementations; all other agents call BFF via typed client. A02 owns shared UI/ChartKit. Operators use the same views without copying entity models. Domain-specific views compose shared components but may have local SCSS Modules.

## 4. Noninterference and compatibility protocol

1. Each agent records BASE_SHA at start and treats shared packages/contract as immutable.
2. Each new file must match exact allowlist; test with a diff linter (I00 to write/execute) before accepting PR. Any path outside rejects that PR until isolated.
3. No one edits common README, root package.json, lockfile or git workflows. Need a dependency? Submit DEPENDENCY_REQUEST.md **in your own feature folder**, including package name, version range, why, license, risk and bundle impact; I00 alone adds.
4. Need route/global nav change? Submit ROUTE_REQUEST.md in own folder; I00 composes route nav and permission gating centrally.
5. Need new BFF endpoint/schema? Submit CONTRACT_CHANGE_REQUEST.md in own folder, including request/response sample, versioning, auth and tenant effect. A01 + I00 agree before implementation; source backend owner still approves if their API changes.
6. Need UI primitive or chart kind? Submit UI_REQUEST.md in own folder, A02 implements globally or defines a narrow import; do not copy and fork shared Button/Status.
7. No cross-feature imports of internal implementation; integrate at route composition layer using public module exports. Circular imports and cross-feature direct access rejected.
8. Workstream agents may use their own synthetic mocks for unit tests; mark them visibly synthetic, and remove accidental demo values from live routes before integration.
9. A01 should publish proposed stable interfaces early; A02 publish primitives early; workstreams can concurrently code against C0 mocks without waiting for backend deployment.
10. All agents leave a PR evidence table with real command output, tests, cases failed/skipped and known missing live services; only I00 marks consolidated E2E after running it.

## 5. Merge graph and execution waves

~~~text
I00: freeze SDD/contract + C0 base & test harness
            | 
            +-- A01 Shell/BFF/identity/contracts ------------------+
            +-- A02 Shared UI + ChartKit --------------------------+
            +-- A03 Task Wizard ----------------------------------+
            +-- A04 Agents/Workflow -------------------------------+
            +-- A05 Runtime/Runs ---------------------------------+--> I00: integration branch
            +-- A06 Quality/Versions ------------------------------+      + API/role E2E
            +-- A07 Ops Core #1–5 --------------------------------+      + real backend seam
            +-- A08 Ops Pipelines #6–10 ---------------------------+      + fail-closed check
            +-- A09 Ops Trust #11–15 ------------------------------+      + staged readiness
            +-- A10 Bilateral builder -----------------------------+
                                                                       |
                                                            owner ADR & acceptance
~~~

**All ten may write independently** after C0. Physical integration sequence is a separate gate: A01/A02 first because they expose common runtime APIs and UI components, then A03/A04/A05/A06, Ops A07–A09 and A10. Integrator must merge/check all on ONE shared revision and resolve schema/route conflicts itself; no agent merges another's code.

## 6. Definition of Ready per packet

- C0 pinned base SHA, route and exclusive paths, contract version, frontend build command, fixtures and preferred design tokens all available.
- Page mock requirements specify source vs demo, exact permissions, empty/loading/error/denied/stale, backend readiness and primary actions.
- No forbidden service topology implementation until ADR owner ratification; mocked UI work can proceed with design-only flags.
- Risk: no unverified release, holdout, cross-tenant data or secrets leak.
- Agents agree not to mark the task DONE if only visual/components pass.

## 7. Definition of Done (four levels, never conflated)

| Level | Evidence | Who can claim |
| --- | --- | --- |
| **DESIGNED** | screen/state/spec, contract, static sample | feature agent with review |
| **COMPONENT_IMPLEMENTED** | feature code + TS/lint/unit + accessibility + story/fixture | feature agent with exact SHA/log |
| **INTEGRATED_STAGING** | actual BFF + backend, schema and security negative cases, Playwright on pinned integration SHA | I00 only |
| **PRODUCTION_VERIFIED** | owner accepted real environment, service IAM, effect proof, release & rollback/monitoring, source data | authorized owner/release process only |

**Mandatory test IDs:** CJM-E2E-001..024 mapped in CJM_UI_CONTRACTS_AND_E2E.md. A01..A10 attach local tests to assigned relevant IDs; I00 creates and runs suite. The two distinct B2B fixtures remain mandatory, bilateral experimental suite is additional.

## 8. Standard task packet receipt / PR description

- Agent ID and exact read documents; BASE_SHA, branch/PR, file ownership diff.
- Feature scope delivered vs explicitly NOT delivered; proposed/live/synthetic API sources.
- Requirement IDs / route IDs / user actions / blocked states.
- Commands and actual unit/component/ts/lint test results on commit SHA.
- Cross-tenant / forbidden-action / holdout / fake-pass negatives as appropriate.
- Screenshots optional for visual evidence; never replace functional tests.
- External backend dependencies, missing DTOs, RFC requests and rollback notes.
- Self-review that no forbidden path changed and no secret/private gold in fixtures.

## 9. What stays outside coding-agent scope

Visual LangGraph graph editor and microfrontends are **ideas only**. A02 can provide a read-only graph visualization primitive **only by distinct reviewed request**, not editor drag/drop. A10 may implement a preview design and contract fixtures for bilateral until two-tenant backend/consent/evaluation becomes genuinely available, and must not pretend to perform real cross-tenant operations.

**No feature agent authorizes changes to owner ADR-0002.** If the integration needs unapproved physical topology, it stays BLOCKED and documented.
## Mandatory live task registry and 2-hour handoff

**Before any coding agent begins, read [TASK_LEASE_PROTOCOL.md](TASK_LEASE_PROTOCOL.md) and its [live GitHub Issue](LIVE_TASK_INDEX.md).** Axx in a work packet is a proposed owner for the module, **not a granted work lease**.

Each worker MUST receive an issue-based task claim through an authorized, serialized coordinator; record server-attributed UTC claim, status, generation, current branch, PR, heartbeat and meaningful progress separately. Heartbeat every <=20min, meaningful progress with linked SHA/PR/test evidence. After >120min without meaningful progress, evaluate compatible AVAILABLE tasks first; only when none exist inspect exact PR state, branch SHA and CI before requesting takeover. Transfer requires coordinator approval and new generation; new owner writes a handoff note and the integrator records it in OpenSpec. No feature agent may edit tasks.md on behalf of other agents.

**Until coordinator and CI are deployed and tested, this rule is required process but NOT technically enforced.** Never claim that a GitHub Issue comment, assignee or label alone is an atomic lock.

## Nine-agent dispatch pack (A01–A09)

**[Copy-paste prompts and current assignments](prompts/README.md)** contains nine standalone Russian instructions, each with exact task Issue, allowed file paths, immediate audit/design activities, conditional coding after I00 C0 and an authorized lease, required tests and evidence report. A10 remains a future advanced bilateral packet, not silently reassigned. I00 handles shared root, integration and task coordinator, not one of the nine.
