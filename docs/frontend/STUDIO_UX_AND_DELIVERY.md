# Agent Factory Studio — UX blueprint, BFF design, integration backlog and acceptance

**Date:** 2026-10-28  
**Implementation priority:** [`STUDIO_MVP_SCOPE_DECISION.md`](STUDIO_MVP_SCOPE_DECISION.md) overrides the full target screen and package inventory below for first pilot.  
**Status:** PROPOSED / design-only. No deployed frontend or automatically ratified ADR.  
**Input:** `AGENT_FACTORY_STUDIO_RFC.md` and `STUDIO_SERVICE_COVERAGE.md`.

## 1. Product design vision and success criterion

Studio makes specialized B2B AI-agent creation and operation understandable without asking business users to compose a graph. The **north-star journey** is: "I describe an operation → attach grounded knowledge → grant precisely scoped access → see what the system built → test actual outputs → inspect independent evidence → approve or reject release → run it repeatedly and monitor outcomes." Time-to-first-verified-value matters more than number of knobs.

**Avoid single-chat illusion.** Conversation is a contextual Business Copilot for proposing task requirements, not the system of record. Every suggested requirement, permission and success metric must be rendered as a structured item with author, source, approval and version. Chat cannot invent credentials or approve unsafe effects.

### Proposed flagship scenario: chemical RFQ

1. A sales leader enters: "Process RFQ XLSX, match each SKU/grade to verified catalog, generate DOCX/XLSX quote draft; never send without approval."
2. System asks for catalog connection and approved template, suggests an exact permitted tool set, highlights missing scopes.
3. User uploads XLSX examples, catalog SOP, template; each artifact receives purpose, rights and parse provenance.
4. Requirements are resolved; expert approves acceptance criteria; immutable READY snapshot created.
5. Orchestrator commands Builder. UI shows tool selection and immutable AgentSpec digest. Each step has a real event/trace.
6. Runtime sandbox attempts a synthetic quote, exposes actual generated file and a **verified** output artifact (not assistant prose).
7. Evaluation independently checks correct matches, required tool effects, safety, regression, cost. If failed, UI shows which assertions failed without revealing sealed gold.
8. If safely repairable, Orchestrator issues GEPARD request; candidate version and prompt/harness diff appears; independent new evaluation required.
9. AgentStore records verified candidate; approval/release policy makes it available to authorized users/A2A callers; production traffic uses pinned version.
10. Regular runs show business documents, review queue, success rate per verified operation, costs, errors and provenance; rollback available if version regresses.

Second acceptance journey: supplier/certificate verification, using different schemas/tools/criteria on same factory source. This proves configurability instead of hardcoded RFQ screens.

## 2. Navigation, responsive layout and role-dependent shell

### Primary customer navigation (max 7 permanent items)

1. **Overview** — KPIs grounded in a time period, action queue, last operations, projects.
2. **Agents** — list, new agent and details.
3. **Runs** — all operations including errors, blocked, costs and artifacts.
4. **Quality** — independent evaluations and comparisons, experiment history.
5. **Integrations** — connector catalogue, scopes, health, data rights.
6. **Releases** — verification, approval requests and version/rollback history.
7. **Workspace** — members, budget, security, notifications, billing (when implemented).

"Agent activity" can be a tab and deep link in the agent page; do not replicate full tables on home and details.

### Operator shell (visible only to authorized platform roles)

- Fleet/Deployments, Workflow queue, Registry Governance, Traces, Evaluation Jobs, Optimizer Jobs, Model Gateway, Security Audit, Incidents/Alerts, Tenants/Support and Platform Settings.
- Global search by authorized `workflow_id/run_id/agent_id/trace_ref`, with no other-tenant existence leaks.
- Context switcher **Customer-safe / Technical** on one agent only when platform authorization allows. Switching doesn't raise privilege.
- Operator-only implementation details are neither in customer HTML nor in API payload (not merely hidden via CSS).

### Global layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ ◈ Agent Factory   Workspace ▾   Sandbox/Prod   Search ⌕   Bell  User │
├────────────────────┬───────────────────────────────────────────────────┤
│ Overview           │  Breadcrumb  /  Contextual actions              │
│ Agents         +   │                                                   │
│ Runs               │  BUSINESS OUTCOME / TRUSTED STATE                 │
│ Quality            │                                                   │
│ Integrations       │  Main content (list | graph | wizard | timeline) │
│ Releases           │                                                   │
│ Workspace          │                                                   │
│ ────────────────── │                                                   │
│ Ops console *      │                                   Action drawer * │
└────────────────────┴───────────────────────────────────────────────────┘
* privilege-bound
```

Desktop target ~1440px; at 1024px split panels collapse; below 768px only summary, approvals and run history have full UX. Graph-heavy inspector stays desktop oriented but still keyboard accessible.

## 3. Detailed views

### 3.1 Overview

Top cards **only with grounded data**: Active released agents, verified completed operations, blocked operations, cost per verified operation, needs action, p95 latency (period and sample). Each displays `source`, `as_of` and empty/no-access if missing. Below: action inbox sorted by severity + age and recent workflows. Do not calculate cost savings or accuracy from unsourced estimates.

### 3.2 Agents catalogue

Search (name, owner, tag), filter task category, environment, release status, readiness and last run; table/card toggles. Row: business goal, owner, active version, verified release status, last operation, spend cap, required actions; never a made-up "agent confidence %" score. Compare versions, open run, duplicate draft from version (new immutable proposal), archive with retention policy. Clear empty state plus create CTA.

### 3.3 New agent — adaptive Business Task wizard

One contextual AI assistant with editable *structured* requirements and an optional "advanced" panel. Five stages:

| Step | Main elements | Required inputs | Grounding/check |
| --- | --- | --- | --- |
| 1 Task | Business objective; result/output; owner; trigger/schedule; prohibited acts | Objective, output, responsible person | Copilot proposes process only from authoritative inputs; human confirms |
| 2 Evidence | Multi-file upload, file purpose, provenance, sample request/output pairs, classification | Approved SOP, reference docs, examples or explicit absence, output schema | Scan MIME/malware, PII/rights, parse statuses; disable READY on unsupported file |
| 3 Connections | Suggested eligible tools with permission scopes, risk/effects, reason selected; OAuth/secure integration handoff | Requested capability, granted tenant-specific scope, supported sandbox endpoint | Registry denies missing permission; no raw credentials in browser |
| 4 Acceptance | Expected format/assertions; negative cases; approvals; tolerance; caps/region/retention | Business-rule owner acceptance, hard veto, min quality, budget, proof | Hidden holdout created by independent Evaluation ACL, never Builder-visible |
| 5 Preflight | Summarized Business Task Package, unresolved answers, selected tools and risk review | READY only after deterministic preflight | Create immutable snapshot, explicit user build command + idempotency key |

Allow save/resume and back navigation while DRAFT. If user edits a READY package, fork a new revision rather than silently modifying issued snapshot. Enforce optimistic concurrency via version/ETag. File parser gives source references per PDF page, XLSX sheet/cell and DOCX paragraph; copilot citations lead to file inspector.

### 3.4 Live factory workflow

A **two-level** display:

- Executive lane: Intake → Tool selection → Build → Sandbox runs → Independent Evaluation → Repair (if necessary) → Verification → Release. Each stage current / completed / warning / blocked / skipped with exact event refs.
- Technical expand: service, command status, `operation_id`, auth classification, event IDs, request version, retry/lease, published artifacts, precise error category, elapsed time, sanitized links to logs/spans.
- Current action strip: reason, required actor, non-destructive next step. Example "Registry rejected `catalog.lookup`: missing `catalog:read` grant; connect read-only catalog." If no safe recovery, show BLOCKED.
- **No fake percent.** Use discrete stages; while waiting display genuine last transition timestamp plus "awaiting result"; if event stream unavailable, show stale badge and poll authoritative GET.

### 3.5 Agent Mission Control (single agent)

Header: name, problem solved, owner, environment, released version, last passed independent eval, risk label, A2A channel status, buttons Sandbox run / Invite reviewer / Release request / Rollback (permission + policy).

Tabs:
- Overview: business result and output types, approved capabilities, constraints and action inbox.
- Playground: text/file request, deterministic input mode, sandbox badge, preview/download output artifact, per-step trajectory and errors.
- Runs: filterable executions, status and external effects.
- Quality: baseline/candidate/holdout provenance, regression, costs, GEPARD report.
- Architecture: read-only LangGraph, MCP nodes, permission edges, memory/checkpoints and A2A boundary.
- Versions & Releases: immutable diffs, channel, risk and approvals, release/rollback evidence.
- Access & Settings: A2A callers, schedules, rate limits, tokens under vault, notifications and retention.
- Advanced technical information in a revealable side panel, not default for all customers.

### 3.6 Playground / run inspector

Three-column desktop layout: request input + attachments / agent transcript + business output / collapsible trusted execution timeline. The transcript is *not* the source of truth. Generated output preview uses signed/authorized artifact fetch; sandbox tools must not take real irreversible action.

Per-step inspector:
- timestamp, service, stage, model route, tool manifest/version and granted scope;
- input/output previews redacted and access-limited; client sees no raw credential or holdout;
- duration, token estimate/actual distinction, provider cost metadata, retry and decision rationale;
- `effect_proof`: VERIFIED_EXTERNAL_RECEIPT vs INTERNAL_RESERVATION vs NONE; the second NEVER counts as the first;
- trace/span link, artifact digest, checkpoint/ref and restart/reconciliation state;
- resume/retry appears only when policy says it is idempotent and approved.

### 3.7 Quality Center

Top: pass/fail/blocked, independent acceptance, safety veto, dataset/version, eval date, sample size; *insufficient evidence* and *unavailable* first-class statuses. Comparison dashboard: baseline vs candidate with immutable spec IDs, business success, side effects, latency p95, total costs and **cost per successful operation** with case count. Surface charts only if denominator meaningful, otherwise blank with explanation.

Detailed tabs:
- Scenario results: allowed public case IDs and safe summaries; sealed holdout correct answers never displayed to optimizer.
- Failures: taxonomy, symptoms, severity, required action, error ownership.
- GEPARD: optimizer status and backend (real GEPA or deterministic mock), allowed change surfaces, before/after prompt diff, budget spent, candidate lineage and re-eval status.
- Model routing: LiteLLM per candidate, provider, region, availability and permitted fallback; no direct provider key display.
- Governance: evidence signatures, independent verifier, who approved, risk and holdout provenance.

### 3.8 Integrations / Registry

Business catalog "What do you need?" categories: ERP, CRM, files, catalogs, messaging, document extraction, compliance. Connector card: supported operations, read/write/effect classification, risk, manifest version, health, owner, source provenance, tenant grant and affected agents.

Installer/config flow is controlled:
1. choose approved connector;
2. show precise scopes and data flow;
3. request authorization from Integration Admin;
4. complete secure OAuth/credential handoff via backend vault;
5. test in sandbox, inspect result and permissions;
6. enable for an agent only in new version/snapshot.

Separate **Registry Governance** for internal roles: submit draft manifest, maker-checker two distinct approvers, provenance verification, schema compatibility, revoke version, impact analysis. No user-uploaded arbitrary MCP server silently obtains production access.

### 3.9 Releases / AgentStore

Version table: digest, author, sources, tool pins, model/prompt/harness revisions, evaluation result and policy, risk, approvals, rollout target, transition history, current serving version.

Release review screen:
- exact immutable candidate;
- independent Evaluation signature and expected run ID;
- all safety / effect / non-regression gates;
- required human approvals (including different approver when required);
- intended runtime environment and A2A audience;
- target deployment health, rollback target and effect risk;
- button `Request release` only when backend currently allows, with clear confirm dialog.
- asynchronous release state never marked RELEASED until AgentStore authoritative transition; deployment health is separate from AgentStore state.
- rollback appends new transition and can need reconcile/traffic routing; does not delete previous version or reverse already committed business effects.

### 3.10 Analytics & billing

Metrics by workspace/agent/version/model/customer task and time window: monthly verified runs, true business-success rate, blocked rate, token usage, model/tool/platform costs, cost per completed operation, spending vs committed caps, latency and queue durations, actual failure causes. Show source and reconciliation completeness for any provider cost. No fake invoices: `Billing` hidden/disabled until commerce backend exists.

### 3.11 A2A + cross-company (P1 optional)

Expose Agent Card, caller grants, invocation history, protocol validation status, per-party privacy-appropriate operation receipts. Optional bilateral inspector: buyer and supplier lanes, shared correlation, public messages, outcomes, costs, and only mutually authorized evidence. No leaked partner prompt, private tools, memory or gold. Sandbox/live label mandatory. Live payment or ordering not auto-enabled.

### 3.12 Internal Operations Console

- Fleet: service/deployment, region, image digest, restarts, health, last integration SHA and drift from active spec.
- Queues/Orchestrator: pending commands, outbox/inbox ACK, duplicate events, stuck workflows, pending approvals, safe retry and DLQ tools.
- Tools & registry: manifest trust state, maker/checker review queue, revoked manifests, denied capability coverage.
- Runtime: trace waterfall, checkpoints, tool effect uncertainty, permission denials, A2A auth failures, memory policy; secrets never logged.
- Quality: evaluation jobs, gold encryption/key availability, signed evidence verifier issues, leases, holdout contamination, expensive model drift.
- Models: LiteLLM provider health, per-tenant limits, model cost, route fallback and counter reconciliation.
- Security: IAM grants, exposed credentials detection alerts, event audit, signer rotation/revocation, tenant scope anomaly.
- Incidents: SLO breach, MTTR, affected tenants/agents, timeline and mitigation/rollback; customer view gets only permissioned impact status.
- Operator assistance: diagnostics suggestions that **never** trigger unaudited releases or payment effects.

## 4. Integration architecture / data model

```text
                  Browser Studio (React/TypeScript)
                 OIDC session, role-aware views
                              |
                   Public Studio BFF / API
   auth, tenant scopes, DTO redaction, read-model, idempotency,
            action authorization, SSE projection, rate limits
                              |
         ┌────────────────────┼──────────────────────────┐
         |                    |                          |
 Task Intake + Artifacts     Control Plane             Query adapters
 (BTP, ingestion, files)    (workflow/AgentStore)      (Registry, Eval,
         |                    |                          Runtime, LiteLLM)
         |          explicit authorized commands        |
         |                    |                          |
 Registry → Builder → AgentSpec versions → Sandbox Runtime
                              |
                  signed independent evidence
                              v
                   Evaluation → GEPARD candidate
                              |          |
                              +── re-eval+──> Control Plane release
                                                     |
                                             approved live Runtime
                                                     |
                                             A2A / direct API
                  telemetry + source-owned event/outbox
                              |
                 sanctioned read projections → BFF SSE
```

No frontend access to databases, raw Kafka topics, internal unredacted traces, LiteLLM keys or holdout vault. **Do not create a new "frontend database" of truth about releases.** An authorized read model can be materialized but must store source version + cursor and reconcile.

### Canonical IDs and relationships

```text
workspace_id/tenant_id
  └─ task_id + task_revision
       ├─ attachment_id / evidence_ref / rights
       └─ task_snapshot_id + digest
           └─ workflow_id + revision
              └─ build_id
                 └─ agent_id + agent_spec_version + artifact_digest
                    ├─ evaluation_run_id + dataset_version_ref + evidence_ref
                    ├─ optimization_run_id -> candidate_spec_digest
                    ├─ release_record_id -> deployment_ref
                    └─ runtime_run_id -> trace_ref -> artifact_refs -> external_effect_receipt_ref
```

Some IDs above are PROPOSED UI-facing identifiers; map to backend actual fields via OpenAPI generated adapters, never assume one ID equals another. Use tenant+resource composite scope. A run may outlive an initial request; asynchronous state should be refetched.

### UI-visible event model (PROPOSED)

```json
{
  "schema_version": "studio.event.v1",
  "event_id": "evt-example",
  "workspace_ref": "w-example",
  "resource": {"kind": "workflow", "id": "wf-example", "revision": 17},
  "stage": "evaluation",
  "status": "NEEDS_ACTION",
  "severity": "warning",
  "reason_code": "MISSING_PERMISSION",
  "required_action": {"kind": "CONNECT_INTEGRATION", "resource_ref": "catalog"},
  "occurred_at": "2026-10-28T08:00:00Z",
  "cursor": "opaque-server-cursor",
  "summary": "Catalog read access is required",
  "evidence_available": false,
  "source": "factory-orchestrator"
}
```

This shape is illustrative and not a live schema. BFF validates source event identity and tenant before projection. Do not send raw event bodies or binary files over Kafka/SSE.

### SSE / reconciliation

1. View GET with `revision` and `as_of`; separately subscribe using `Last-Event-ID` opaque resume cursor.
2. Event has tenant-scoped validated source and sequence. Update cache only if not stale/duplicate.
3. Gap, reconnect, 410 retention expiry, out-of-order events or service error → refetch snapshot; never show an older state as new.
4. Poll 5–10 s fallback with exponential backoff; do not run thousands of browser sockets per agent card.
5. Browser clock is presentation only; timestamps, states, actions, costs and approvals are server authoritative.

### BFF responsibilities / hard boundaries

- Authenticate OIDC browser via server-only session cookie (HttpOnly, Secure, SameSite). CSRF for state mutation, CSP and upload restrictions.
- Aggregate services with typed versioned DTOs and independent timeout/circuit breaker; return partial overview with explicit `unavailable` sources rather than fabricated zeros.
- Enforce least-authority tenant/user/project policies on *every* command including stream subscriptions and signed file downloads; service account can never use client input to elevate scope.
- Map error codes to safe i18n business language and operator diagnostic IDs; no stack traces/tokens/prompt secrets.
- Append audit actor/action/target/justification to appropriate owner service; BFF event not source of independent audit proof.
- Generate idempotency key per explicit operation (not per click render), prevent accidental repeated submissions, and maintain action receipts.
- Protect upload with signed short-lived upload capabilities, file quotas, metadata/purpose policy and scanner before indexing.
- Create separate rate limits for heavy agent runs, evaluation, optimization, file processing, registry mutations, release and rollback.

## 5. Suggested modular frontend structure (pending ADR)

```text
apps/studio-web/
  app/[locale]/w/[workspaceId]/{overview,agents,runs,quality,integrations,releases,analytics,settings}/
  app/[locale]/ops/{fleet,workflows,jobs,registry,traces,incidents,audit,providers}/
  features/{task-wizard,agent-list,agent-mission-control,workflow-timeline,run-inspector,
            quality-comparison,tool-catalog,release-console,usage-analytics,ops-fleet}/
  entities/{agent,workflow,run,tool,quality,release,workspace}/
  shared/{ui,api,auth,permissions,events,telemetry,i18n,feature-flags}/
packages/{ui,contracts,design-tokens,test-fixtures}/
```

**Confirmed recommendation for design review:** strict TypeScript, React + Next.js, **SCSS Modules + CSS custom properties** and a tokenized shared UI kit, pnpm workspaces + Turborepo for TypeScript packages, TanStack Query, accessible primitives, Zod runtime checking for selected DTOs and OpenAPI code generation. React Flow is for read-only graph inspector initially. CSS/tokens and performance constraints are in [`STUDIO_SCALABILITY_ENGINEERING.md`](STUDIO_SCALABILITY_ENGINEERING.md). Avoid mirroring server state into one global store.

## 6. Detailed feature and delivery dependencies

### Wave 0 — contract and security design (foundation, not frontend screenshots)

- Determine tenant/Workspace and identity ownership; choose independent BFF vs Next.js server gateway; owner ratifies ADR.
- Model all entities, state machines and existing Java/Python API differences; no cross-microservice direct DB access.
- Approve private/public DTO redaction, release policy, evaluation evidence and tool-effect receipt semantics.
- Design 10 core screens + mobile and empty/failure states; validate with 3 roles: business owner, operator, integration owner.

### Wave 1 — read-only useful customer/operator product

- OIDC login and tenant isolation.
- Home (real actionable workflow status), agents list/detail, existing workflow timeline/audit, candidate version, safe agent/run inspector and Ops health.
- Real source flags; no fake creation or release. Deep links and filters.
- Tests: 401/403, tenant isolation, revision reconciliation, API outages, stale SSE, keyboard navigation.

### Wave 2 — real business task creation and operation

- Implement Task Intake and artifact/ingestion owners; upload/validate/READY snapshot.
- Registry discovery & consent integration, explicit permission and missing-capability action.
- Orchestrator → Builder command, generated AgentSpec and sandbox run.
- Quality scorecard from signed Runtime evidence, independent eval and business artifacts.
- Actions: draft save, build start, sandbox run, request additional permissions.

### Wave 3 — controlled agent optimization, release and monitoring

- Real GEPARD provider tests (do not label mock as GEPA); independent holdout; comparison and budget.
- Real AgentStore release approvals, deployment intent/result, trusted A2A ingress, version rollback.
- LiteLLM persisted budgets, usage reconciliation, trace spans, incident/notification routing, per-agent SLO.
- Role-based operational actions with audit.

### Wave 4 — optional and commercial scaling

- Bilateral A2A scenario lab, partner-specific data access and cross-organization consent.
- Soup specialized training and licensed data rights.
- Commercial subscriptions/billing, marketplace and sophisticated visual editor ONLY when usage proves need.
- Pi Durable stays research benchmark outside selected Python MVP.

## 7. Acceptance criteria for every screen

| Concern | Tests required (examples) |
| --- | --- |
| Contract | GET real source: expected schema/version; missing field -> safe unavailable, not fabricated values |
| Authorization | A role without permission cannot see unauthorized data through cards, previews, SSE, search, download, or direct URL |
| Tenant | Two-tenant E2E: all API/search/event counters and artifact signed URLs isolated |
| Async | Retry/reconnect/out-of-order events: monotonically correct timeline, current truth after refresh |
| Idempotency | Double-click build/release/rollback does not create duplicate action or business effect |
| Evidence | Model claims completion but no real output/effect -> blocked; unsigned or tampered audit -> no PASS |
| Approval | UI enabling/disabling button never bypasses server gate; unauthorized mutation stays denied |
| Files | Oversized/malicious/ambiguous format rejected; safe provenance and classification preserved |
| Budgets | Server enforced spend/steps/tokens; UI reflects authoritative budget and incomplete billing |
| Observability | Source trace correlated by trusted IDs; credentials/holdout/private tenant info not in logs |
| Accessibility | Keyboard reachable, focus preserved in drawers/modals, semantic live status, contrast and reduced-motion |
| Reliability | BFF partial outage, request timeout, stale data, degraded SSE, rollback and restart safely represented |
| Internationalization | RU/EN, locale-safe date/time, currency and number formatting, meaningful errors |
| Performance | Proposed, to be measured: initial shell interactive p75 under 3s on target client; filters/search under 500ms p75 server-dependent; event-to-view p95 under 3s when healthy |

Targets are hypotheses, not actual SLO measurements. Separate contract tests, browser Playwright E2E, security negative suites and production canary/read-only telemetry.

## 8. Implementation backlog with explicit dependencies

| ID | Priority | Deliverable | Upstream dependency | Definition of done |
| --- | --- | --- | --- | --- |
| UI-001 | P0 | Workspace+OIDC+BFF authorization | tenant identity/ADR | authorized session, deny-all cross-tenant negative tests |
| UI-002 | P0 | Design system + navigation + typed routing | UI-001 | RU/EN, responsive, accessibility |
| UI-003 | P0 | Source capability/status projection | service discovery + UI-001 | no fake actions/data; degradation states |
| UI-004 | P0 | Workflow timeline and action inbox | CP OpenAPI + event/read model | correct revisions/events; targeted resolution |
| UI-005 | P0 | Agents list + mission control | AgentStore + CP read adapters | accurate versions/releases, empty/outage states |
| UI-006 | P0 | Run inspector / sandbox result | Runtime safe run API | verified business output vs prose, trace redaction |
| UI-007 | P0 | BTP wizard / draft & revision | Task Intake + artifact service | real upload, preflight, READY snapshot, idempotent build |
| UI-008 | P0 | Integrations consent + Registry discovery | Registry HTTP / credential vault | least privilege, maker checker, no raw secrets |
| UI-009 | P0 | Independent Quality scorecard | Eval signed audit API | cases/effect proofs/holdout exposure gates |
| UI-010 | P0 | Release and rollback gate | CP/AgentStore + deployment | no client-side RELEASED; server approval and safe rollback |
| UI-011 | P1 | GEPARD candidate diff and experiment board | actual optimizer + eval | baseline pinned, re-evaluation and budget, no fake improvement |
| UI-012 | P1 | LiteLLM model usage/cost/SLO | persistent proxy + cost reconciliation | per-success cost trustworthy, provider key hidden |
| UI-013 | P1 | Ops console: fleet/traces/outbox/incidents | OTel/Langfuse/Kafka/service health | searchable authorized traces, alerts, safe retries |
| UI-014 | P1 | A2A Caller management and invoking | released runtime + official SDK | positive and denied client tests |
| UI-015 | P1 | Notification delivery and assignment | event projection + preferences | read/ack, dedupe, routing, no sensitive leak |
| UI-016 | P2 | Paired buyer/supplier A2A board | bilateral protocol + consent | per-party privacy, frozen experimental versions |
| UI-017 | P2 | Soup experimental training console | model rights + GPU worker | approved data, independent retest and budget |
| UI-018 | P2 | Billing & plans | commercial provider/legal decisions | reconciled usage and invoice authorization |
| UI-019 | P2 | Optional visual graph editor | graph config schema/migration | graph cannot escalate scopes, expert only |

## 9. Decision checklist for owner/architecture review

1. **UX**: business-first wizard + optional technical inspector, single studio and privileged ops shell?
2. **Service boundaries**: Task Intake module vs service, artifact ingestion worker, read model / BFF, isolated tenant databases, who owns identity?
3. **Launch contract**: is P0 read-only first or full sandbox create/run before customer demo? No action button until genuine upstream enabled.
4. **Product safety**: what side-effect classes allowed in the first pilot, who approves release, and does automatic low-risk promotion need human opt-out?
5. **Payments and A2A**: bilateral A2A and actual irreversible actions remain optional and separately approved.
6. **Operational SLO**: chosen region, data retention, metrics provenance, customer-visible incident status, security ownership.

**Review required before treating this as official architecture.** This is an integration blueprint, not implementation proof.
