# Agent Factory Studio — executable CJM and screen-level product specification

**Status:** PROPOSED / ready for owner and integrator review, NOT implemented. **Date:** 2026-10-28.
**Canonical requirements:** openspec/changes/studio-cjm-parallel/specs/studio-cjm/spec.md. This blueprint specifies UX and testable interactions; it does not ratify ADR-0002 or grant any service authority.
**Scope:** full intended boxed product incl. mandatory 15-section Operator Console, chart kit, advanced bilateral A2A builder, future-only LangGraph editor + microfrontends. Actual backend availability is dynamically gated (see STUDIO_CAPABILITY_API_CONTRACT.md).

## 0. Core user promise and measurable success

The user is buying a **verified, repeatable business result**, not a graph editor or a demonstration LLM chat. A business owner must be able to provide a problem, approved evidence and integrations; observe creation, obtain a real sandbox artifact, understand independently checked quality and only then approve safe release. Technical details are accessible to authorized operators on the same domain object IDs, not exposed to every customer.

**North-star outcome:** Time to First Verified Value (TTFVV) = first independently accepted business output timestamp minus initial task draft creation timestamp. Track separately total elapsed, user waiting, approval waiting, queue time, execution, evaluation and support intervention. Report only if both timestamps and independent evidence exist. Secondary metrics: draft→READY, READY→build, first sandbox result, quality pass rate, cost per independently accepted operation, blocked reasons, escalation rate, time to resolution, retention and incident impact. All require source provenance, time range and denominator.

## 1. Personas, permissions and journeys

### Personas
- **Business Initiator (BI):** creates drafts, submits samples, starts permitted sandbox workflows, reads own artifacts.
- **Business Domain Approver (DA):** confirms authoritative rules, evaluation acceptance and approves business use within scope.
- **Integration Administrator (IA):** connects approved ERP/MCP/API scopes, grants least privilege, audits connection health; cannot promote an unsafe agent.
- **Agent Operator (AO):** inspects workflows, runs and verified evidence; can request permitted safe retries or approvals, no blanket admin.
- **Workspace Owner (WO):** manages members and contractual visibility; not a substitute for independent evaluation.
- **Platform Operator (PO):** uses 15-section Ops Console with separately granted resource-specific abilities, does not automatically own customer documents.
- **Auditor (AU):** read-only authorized immutable audit/evidence, sanitized according to data classification.
- **External A2A Caller (AC):** can invoke released agents only through scoped identity and published A2A contract.
- **Bilateral Company A/B Owner (BA/BB):** independent authority over each company's BTP, tools, memory, approval and release; shared content only by explicit consent.

RBAC, feature capability gates and tenant scope are SERVER authoritative. Business role may see fewer explanation fields than operator. No role may read sealed holdout correct answers outside trusted Evaluation authority.

### CJM stages and entry points

| Stage | Actor goal | UI surface / route group | User-triggered command | Actual source and completion evidence | Progress + error behavior |
| --- | --- | --- | --- | --- | --- |
| J00 Access | choose organization and environment | Workspace selector; sign-in | select authorized workspace | OIDC session / trusted workspace grants | forbidden workspace gives neutral denial; reset stale cache on switch |
| J01 Discover | know next action | Agents / dashboard | create new, resume draft, open blocked workflow | AgentStore, Orchestrator, Task Intake read projection | zero vs unavailable vs stale counts distinct |
| J02 Define | explain desired business outcome | Create Agent wizard | save draft, edit inputs/outputs/business objective | Task Intake, revision + ETag | autosave acknowledgement, recover conflict without lost changes |
| J03 Ground | attach SOP/examples/templates | attachments step | upload, purpose-tag, classify, retry rejected upload | Artifact ingestion metadata and immutable hashes | per-file uploading/parsing/clarification/approved/failed; provenance |
| J04 Authorize | allow minimally sufficient tools | integrations step | request grant, connect via vault flow, inspect risk | Registry selection, Integration Admin consent | missing scopes/risk/health deny READY |
| J05 Preflight | confirm exactly what will be built | review/ready | approve interpretations, validate, freeze snapshot | READY immutable TaskSnapshot, responsible owner | list missing fields and actor-specific action; edit creates new revision |
| J06 Build | initiate actual creation | workflow page | explicit idempotent Start Build | Orchestrator → Builder command, build ID & immutable AgentSpec | read true state, no fake percentage; safe refresh/poll |
| J07 Test | verify sandbox business result | Playground / Run detail | submit test input, inspect artifact | Runtime output, tool calls, safe evidence, trace | blocked on unsafe effects; artifact must be genuinely stored |
| J08 Evaluate | understand independent result | Quality | request allowed eval, inspect test summary | Evaluation, sealed holdout check, signed run evidence | PASSED/FAILED/BLOCKED/INCONCLUSIVE independent of agent self-report |
| J09 Improve | recover from failures safely | Quality / Candidate | request allowed bounded optimization, compare | GEPARD+Orchestrator; independent re-evaluation | mock optimizer clearly labelled; budget/attempt cap enforced |
| J10 Approve | decide if candidate can ship | Versions/Release | request review, approve if scoped | AgentStore/Control Plane signed evidence, release policy | pending approval ≠ deployed; 403/409 with reason |
| J11 Operate | send repeat tasks / consume files | Agent detail, Runs, authorized A2A | run task, download artifact, perform permitted approval | released Runtime/A2A, external receipts | no unverified external effect shown as done |
| J12 Monitor | improve costs, safety, availability | Analytics, Ops | filter verified metrics, investigate; permitted rollback | LiteLLM/Eval/OTel/deployment telemetry and authoritative release | missing telemetry shows unavailable; explain last observation |
| J13 Escalate | resolve blockers or incidents | action inbox, operator deep link | request approval, open incident, retry allowed safe command | source-owned audit and incident log | who owns action, why blocked, safe fallback and follow-up |

Only trusted server state can move from DRAFT to READY or VERIFIED to RELEASED; frontend suggests, never self-certifies.

## 2. Complete screen contracts and UX behavior

### SC-01 Agents + overview (/w/:workspace/agents, optional /overview)

**Cards/rows:** agent name, business outcome, owner, sandbox/production, immutable serving version, independent evaluation status and sample size, latest actual run, cost if verified, blocker, next permitted action. Search and filters in URL; server pagination and stable sort. New agent, resume draft, open workflow, open agent, view evidence. Empty: "Пока нет агентов"; denied: no existence leaks; unavailable: "Источник недоступен" instead of zero; stale: show as_of.

**CJM edge:** user with incomplete draft returns to exact stage and sees autosaved revision; last selected workspace must be validated against fresh session before any subsequent API request.

### SC-02 Guided Create Agent wizard (/w/:workspace/agents/new, /tasks/:id)

Steps can group 3–5 sections based on content but must cover these validated contracts: Objective/trigger/output/person accountable; file purpose and provenance; integration capabilities and risks; acceptance assertions and hard limits; reviewed normalized snapshot. Copilot may suggest grounded structured rules using source citations, but cannot silently accept, grant or submit.

**Controls:**
- Start: name, business objective, process steps/exceptions, input/output typed format, human approval before consequential effects.
- Files: drag/drop, per-file progress, hash/purpose (BUSINESS_RULES, REFERENCE_KNOWLEDGE, INPUT_EXAMPLE, SOLUTION_EXAMPLE, TUNING_CASE, VALIDATION_CASE, OUTPUT_TEMPLATE, CONNECTOR_CONTRACT, SEALED_HOLDOUT only Evaluation-owned flow), rights/PII, provenance page/sheet/row. Block unsupported/malicious/missing files.
- Integrations: eligibility reasons, requested tool manifests versions, required scopes/effects, real consent. "Request access" opens correct admin workflow, never grants itself.
- Acceptance: concrete success cases and forbidden effects; min quality, max spending, time/attempt limits, policy owner. Hidden gold not exposed through wizard data.
- Preflight: diff proposed vs approved requirements, unresolved clarification list, matching result, budget, selected scopes; "Validate" and "Freeze READY" separate from "Build".

**State mechanics:** autosave with debounce + explicit saved/unresolved status; optimistic revision conflict 409 surfaces merge/reload choice and preserves user's unsaved form; on READY edit fork task revision, never mutate frozen snapshot. On upload failure preserve draft and allow per-file retry. Invalid BTP => no build button with exact blocker codes and safe remediation.

### SC-03 Agent Mission Control (/agents/:agentId/overview)

Summary: task objective, pinned AgentSpec digest/version, execution environment, trust/quality evidence, selected trusted tools, memory/checkpoint policy (redacted), A2A card/public scope status, last verified run, cost and approvals. Tabs: Overview, Playground, Runs, Quality, Architecture (read-only future inspector), Versions, Access. CTA offered only from server allowed_actions; production and sandbox visually distinct. Show source_as_of, revisions, changed-since-validation warning; no misleading red/green for unproven evidence.

### SC-04 Workflow Timeline (/workflows/:workflowId)

Display user-facing stages Intake / Permissions / Build / Sandbox / Evaluation / Optimize or Blocked / Verified / Release with associated source service and real event time; **skip** clearly when no optimizer necessary. Collapse technical details per stage with operation ID, trace, version, reason code, retries, spent budget, and event provenance to authorized AO/PO. Poll current GET while active; when source unreachable, show last known state and staleness, never infer completion. Out-of-order revision cannot move visually backwards. "Cancel" only if backend actual cancellation semantics exist; unsafe effects need reconciliation. Double start click must preserve a single idempotency receipt.

### SC-05 Sandbox / Run Inspector (/agents/:id/playground, /runs/:runId)

Inputs: text, sample JSON or approved file depending on task contract. Always show "Sandbox" and side-effect policy. Output: real artifact preview/download via scoped signed link; evidence outcome distinct from LLM answer. Timeline shows allowed tool calls, effects, model route, cost, logs and provenance according to rights. Explicit effect categories VERIFIED_EXTERNAL_RECEIPT / INTERNAL_RESERVATION / UNCONFIRMED / NONE / RECONCILIATION_REQUIRED. Do not allow retry of unsafe committed action without server reconciliation. Concurrency: two simultaneous runs displayed independently; preserving exact run_id.

### SC-06 Quality & Versions (/agents/:id/quality, /versions)

Independent scorecard: dataset version, baseline/candidate spec digests, number of safe cases, hard veto, business output, failed evidence categories, signed proof verification, cost/latency with sample count and provenance. Cases may display redacted aggregate summaries only; sealed holdout answers never in UI, BFF, logs or client cache. GEPARD experiment: baseline pinned, allowed optimization surfaces, attempt/budget cap, before/after candidate diff, retest status, model adapter truth (deterministic mock != live GEPA). Versions: immutable revision diff and approvals, source-authoritative RELEASED/ROLLED_BACK; output can be VERIFIED but waiting release. Release/rollback confirm dialog includes impact, target version, permitted scopes, idempotency, blocked reason and audit ID; no client-optimistic release.

### SC-07 Workspace & notification inbox

Roles/members and grants; clear ownership for human approval tasks. Action inbox severity/action owner/category, status and source; mark-read only as notification state, not domain approval. Consent and connector expiry alerts. Email/slack/push integration only if backend available, otherwise safe planned status. Billing page not active until commercial backend exists.

### SC-08 Operator Console (mandatory 15 modules)

Operator shell navigation exposes 15 exact modules listed in STUDIO_BOXED_PRODUCT_FEATURES.md: Fleet, Workflows & Queues, Builder & AgentSpecs, Runtime & Checkpoints, Registry, Connectors & Secrets, Task Intake & Artifacts, Evaluation & Holdouts, GEPARD Experiments, Models & LiteLLM, A2A & Bilateral Lab, Releases & AgentStore, Observability, Security/Tenants/Audit, Incidents/Alerts/SLO. Each **must** have a design, authorized route, query DTO, filters, drill-down, table/graph when sourced, empty/error/denied/stale variants and audit for each permitted mutation. Operator-level tenant visibility is separately scoped; no global raw view by default.

Key operator action per module: Fleet inspect and diagnose; Workflows investigate safe retries/queues; Builder compare immutable specs; Runtime inspect checkpoint and effects; Registry maker-checker/revoke; Connectors inspect credentials health not values; Artifacts inspect provenance and failed parse; Evaluation diagnose independent evidence without gold; GEPARD inspect candidates and control budget; Models inspect routes/spend; A2A inspect protocols/consented pair; Releases review and rollback; Observability inspect spans; Security audit grants and revocations; Incidents acknowledge/assign/mitigate. A source lacking APIs gets precisely **NOT_CONNECTED**, never synthetic operational data. All high-impact commands require server reauth+policy, justification, confirmation and event audit.

### SC-09 Typed analytics library (mandatory)

Expose 15 chart templates described in STUDIO_BOXED_PRODUCT_FEATURES.md, use **one candidate engine (Apache ECharts)** behind shared typed adapter. No feature team can directly invent chart type/source policy or ship demo metrics as real. Every displayed chart includes source, period, timezone, unit, sample size, completeness, last observed, authorized drill-down, accessible table/summary, empty and redaction modes. For revenue/cost and verified quality never average incompatible samples or treat null as zero. Chart modules lazy-load; large trace series paginated/aggregated server-side. The chart kit is mandatory to implement as a reusable capability, but data-backed chart instances unlock when source proves trustworthy.

### SC-10 Two-company collaborative factory (committed advanced module)

User can select "One company" or "Two companies A2A", but second mode is disabled with a grounded reason until bilingual tenant consent+backend integration gates pass. Organizer sends expiring invite; **both** organizations independently approve BTP/revisions, grants and disclosure. Two separate Builder calls produce A0/B0 immutable AgentSpecs, two isolated Runtime sandboxes exchange only approved A2A messages. UI displays A timeline / shared disclosed messages / B timeline with role-controlled redaction. Independent Evaluation A, B, joint result; GEPARD candidates cross-play A1×B0, A0×B1, A1×B1 with each tenant's separate gold; one organization's optimization never silently updates the other. Separate release approvals and compatibility checks, consent revocation and offline partner handling. The feature is product-committed, NOT first-pilot readiness.

### SC-11 Roadmap only: visual LangGraph editor and microfrontends

Record design ideas and dependencies, no implementation tasks for drag/drop editor or Module Federation. Read-only graph inspector only when real graph metadata is available and wanted. Future graph editor must produce a validated immutable candidate and independent quality; future microfrontend extraction must preserve one OIDC, tenant policy, stable contracts, shared tokens and rollback. A roadmap card must not have an enabled "edit graph" or "independently deploy" action.

## 3. Mandatory state model & communication

Never conflate:
- Task Intake DRAFT / UPLOADING / INGESTING / REQUIRES_CLARIFICATION / VALIDATED / READY_FOR_BUILD / SNAPSHOTTED;
- Workflow DRAFT / READY / BUILDING / TESTING / OPTIMIZING / TRAINING / RE_TESTING / VERIFIED / BLOCKED / RELEASED / ROLLED_BACK (exact Control Plane draft enum; no fake percentages);
- Build QUEUED / RUNNING / ASSEMBLED / FAILED / BLOCKED;
- Runtime run QUEUED / RUNNING / COMPLETED / FAILED / BLOCKED / RECONCILIATION_REQUIRED (proposed view union, not an assertion of current backend);
- Independent evaluation QUEUED / RUNNING / PASSED / FAILED / BLOCKED / INCONCLUSIVE;
- AgentStore CANDIDATE / VERIFIED / RELEASED / ROLLED_BACK;
- Feature ROADMAP_IDEA / PLANNED / DISABLED / PREVIEW / AVAILABLE / DEGRADED / FORBIDDEN.

Unknown state is UNKNOWN_UNSUPPORTED_VERSION, disables privileged mutations. Success toast only after a confirmed command receipt; final completion only from authoritative GET. Every async command returns command/workflow id + idempotency and source ref, not a fabricated UI state. Unauthorized returns 401/403 and no existence leak, revision conflict 409 with resolution, 429 with retry guidance, 503 with last known snapshot, 202 pending with a real tracking ID.

## 4. Negative journey catalog (must become E2E)

- JN01 missing business rule, conflicting SOPs; cannot freeze READY.
- JN02 disallowed/malformed XLSX/PDF/DOCX/CSV/JSON/OpenAPI, oversized uploads, type spoofing, PII classification/rights denied.
- JN03 no approved tool, scope missing, revoked tool or stale schema; safe explanation, no implicit grant.
- JN04 rapid double-click build and two tabs; exactly one semantic operation per idempotency scope.
- JN05 Builder fails, times out, restarts; no false "assembled", last state persisted.
- JN06 Runtime tool denied, external effect reserved but no receipt; run and Evaluation do not PASS.
- JN07 Evaluation unavailable, signature forged, hidden holdout collision/leak attempt; never show PASS and never reveal gold.
- JN08 GEPARD candidate regression, attempt/time/cost cap, LIVE vs MOCK distinction; no silent promotion.
- JN09 approval denied, version stale, deployment absent, 403/409 or manual release withheld; never RELEASED.
- JN10 tenant switch while workflow active, URL forgery, SSE/poll cross-tenant data, cache contamination; fail closed.
- JN11 network offline/reconnect after partial command acceptance; recover by stable idempotency operation receipt without duplicates.
- JN12 graph has 10k spans, run has many steps; accessible virtualized/paginated inspector without unbounded browser download.
- JN13 bilateral: only A consent, B revokes, partner offline, private prompt/eval gold in message; block and redact.
- JN14 operator cannot access customer secret, sealed gold, another tenant, or elevated release based on UI navigation.
- JN15 no trusted cost/time series source; chart displays unavailable, not zeros or fabricated sample data.
- JN16 malformed/unrecognized BFF API status; unknown safe state, never fake success.

## 5. Interaction content and accessibility

Primary copy in Russian with English internationalization keys; every error has human reason + precise next action + source-defined reason code in technical expandable details. Loading skeleton distinct from processing; "not found" distinct from permission denial without leaking other tenant existence. Use text+icon for status, focus management in dialogs, keyboard controls, aria-live only for meaningful terminal updates, accessible visualizations with tables, dark/light themes via SCSS Modules and CSS variables, reduced motion; mobile permits core read, approval and status while heavyweight trace may be desktop-first.

## 6. Delivery/acceptance promise

A feature is DONE only when route/UI, typed BFF contract, real source integration, tenant/role negative tests, error/empty/degraded state, documented test run and independent E2E verification on a pinned SHA all pass. A mock-only page may be accepted as a UX artifact but NOT as a working product feature. If a backend does not exist, present preview-only design and keep implementation unchecked.

**Owner signoff dependency:** service topology and deployment choices remain pending ADR-0002. This change defines logical product behavior and a safe parallel frontend work plan without owner-authorizing new physical microservices.