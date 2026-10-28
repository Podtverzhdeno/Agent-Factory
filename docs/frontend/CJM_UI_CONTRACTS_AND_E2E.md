# Studio CJM — frozen proposed frontend ports, DTOs, states and E2E contract pack

**Status:** PROPOSED v0, no live endpoints asserted. Scope freeze for parallel frontend implementation; changes require an integrator-owned contract change request.  
**Architecture:** browser → Next.js server-only BFF → authenticated service adapters → source service. Never browser → internal Java/Python services, raw DB, Kafka, Langfuse admin endpoint, model provider or secret store.

## 1. Shared public contracts / implementation convention

- The integrator owns a **single canonical frontend read contract** in this doc before agents work. Backend OpenAPI owners remain authoritative; Studio BFF maps service DTOs (including newer/proposed versions) to stable view DTOs. Never rewrite Java/Python OpenAPI from a feature branch.
- TypeScript exact signatures are **PROPOSED** and must be validated against actual upstream APIs before live wiring. Unknown statuses fail closed.
- JSON field naming in public UI BFF is camelCase; service DTO mapping handles internal snake_case. Dates RFC3339 UTC; amounts decimal string + ISO 4217 currency (not untyped floating point financial totals).
- All IDs are scoped by authorized workspace and environment server-side; path workspace is not authorization.
- All list APIs accept cursor + bounded limit; response includes items, nextCursor, sourceAsOf and completeness. Implement server-side paging and filter, no unbounded download.
- Common request headers: trusted server session, CSRF for writes, idempotencyKey for commands, If-Match or expectedRevision for draft edits. The server generates/validates trace correlation; do not echo untrusted raw headers into audit.
- File upload: request signed, scoped, short-lived upload permission, then verify the artifact ingestion status. No binary via Kafka or SSE. Download via authorized short-lived reference, no public permanent link.

## 2. Shared immutable types (conceptual, exact TS source owned by contract/platform agent)

~~~ts
export type SourceState =
  | "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "STALE" | "UNSUPPORTED";
export type EffectiveFeature =
  | "ROADMAP_IDEA" | "PLANNED" | "DISABLED" | "PREVIEW"
  | "AVAILABLE" | "DEGRADED" | "FORBIDDEN";
export type BusinessAction =
  | "task.save" | "task.upload" | "task.validate" | "task.ready"
  | "workflow.start" | "runtime.sandbox_run"
  | "evaluation.request" | "optimization.request"
  | "release.request" | "release.approve" | "release.rollback"
  | "integration.request" | "incident.acknowledge" | "audit.export"
  | "bilateral.invite" | "bilateral.consent" | "bilateral.evaluate";
export interface SourceStamp {
  source: string; sourceAsOf: string | null;
  completeness: SourceState; revision: string | null;
}
export interface ActionDescriptor {
  id: BusinessAction; allowed: boolean; reasonCode?: string;
  requiresConfirmation: boolean; requiresApproval: boolean;
}
export interface SafeError {
  code: string; messageKey: string; retryable: boolean;
  requiredAction?: string; requestRef?: string; source?: string;
}
export interface Page<T> {
  items: readonly T[]; nextCursor: string | null;
  stamp: SourceStamp;
}
export interface TaskView {
  taskId: string; revision: string; status: string;
  objective: string; ownerRef: string; missingRequirements: readonly string[];
  artifactCount: number | null; snapshotRef: string | null;
  allowedActions: readonly ActionDescriptor[]; stamp: SourceStamp;
}
export interface AgentSummary {
  agentId: string; displayName: string; businessOutcome: string;
  ownerRef: string; environment: "SANDBOX" | "PRODUCTION";
  candidateSpecDigest: string | null; releasedSpecDigest: string | null;
  quality: "PASSED" | "FAILED" | "BLOCKED" | "INCONCLUSIVE"
         | "UNAVAILABLE" | "UNKNOWN_UNSUPPORTED_VERSION";
  latestRunAt: string | null; actionRequired: string | null;
  stamp: SourceStamp;
}
export interface WorkflowView {
  workflowId: string; taskSnapshotRef: string; agentId: string | null;
  backendState: string; displayStage: string; revision: number;
  pendingOperationId: string | null; requiredAction: string | null;
  spent: {amount: string; currency: string} | null;
  stamp: SourceStamp;
}
export interface RunView {
  runId: string; agentId: string; specDigest: string; environment: string;
  status: string; outputArtifactRefs: readonly string[];
  effectVerification:
    | "NOT_REQUIRED" | "UNCONFIRMED" | "CONFIRMED_BY_EXTERNAL_RECEIPT"
    | "RECONCILIATION_REQUIRED" | "UNAVAILABLE";
  traceRef: string | null; usage: {amount: string; currency: string} | null;
  stamp: SourceStamp;
}
export interface EvaluationView {
  evaluationRunId: string; specDigest: string; datasetRevision: string;
  status: "PASSED" | "FAILED" | "BLOCKED" | "INCONCLUSIVE" | "UNAVAILABLE";
  independentVerified: boolean; evidenceRef: string | null;
  requiredEffectsVerified: boolean | null;
  cases: {passed: number | null; total: number | null};
  stamp: SourceStamp;
}
export interface FeatureAvailability {
  featureId: string; scope: string; stage: string;
  availability: EffectiveFeature; evidenceLevel: string;
  reasonCode: string | null; allowedActions: readonly BusinessAction[];
  stamp: SourceStamp;
}
~~~

**Do not use these exact interfaces blindly for deployment.** Contract owner must align them to real APIs, validate unsafe/null/unknown data at runtime, and prevent PASS or RELEASED from appearing merely because a field is string-typed.

## 3. Required browser-facing BFF routes / command semantics

| Public BFF route | Method | Read/command | Authority | Consumer |
| --- | --- | --- | --- | --- |
| /api/studio/me | GET | session workspace grants, role, locale, safe user profile | IAM | platform + shell |
| /api/studio/capabilities | GET | evidence-backed feature availability | BFF from service/source + IAM | shell + every module |
| /api/studio/agents | GET | cursor list AgentSummary | AgentStore / CP | agent list |
| /api/studio/agents/:id | GET | Agent detail + pinned specs | AgentStore / CP | Mission Control |
| /api/studio/tasks | POST/GET | create or list draft BTP | Task Intake | creation |
| /api/studio/tasks/:id | GET/PATCH | revisioned edit with If-Match | Task Intake | creation |
| /api/studio/tasks/:id/uploads | POST | short-lived permission + artifact receipt | Artifact ingest | creation |
| /api/studio/tasks/:id/validate | POST | missing fields and structured blockers | Task Intake | creation |
| /api/studio/tasks/:id/ready | POST | immutable READY snapshot | Task Intake | creation |
| /api/studio/registry/eligible | GET | approved capabilities, scope denials | Tool Registry | creation / Ops |
| /api/studio/integrations/:id/request | POST | permission workflow request | IAM / Integration owner | creation |
| /api/studio/tasks/:id/builds | POST | accepted command + workflow ID/idempotency | Orchestrator | workflow |
| /api/studio/workflows/:id | GET | WorkflowView | Orchestrator | workflow |
| /api/studio/workflows/:id/audit | GET | sanitized transitions | Orchestrator | workflow + Ops |
| /api/studio/agents/:id/runs | GET | cursor list | Runtime | runs |
| /api/studio/agents/:id/sandbox-runs | POST | safe scoped run command / receipt | Runtime | playground |
| /api/studio/runs/:id | GET | RunView including safe evidence | Runtime | run inspector |
| /api/studio/artifacts/:id/access | POST | authorized ephemeral artifact access | Artifact store | runs / intake |
| /api/studio/agents/:id/evaluations | GET/POST | evaluations; POST independently authorized | Evaluation + Orchestrator | quality |
| /api/studio/agents/:id/optimizations | GET/POST | candidate history; POST bounded request | GEPARD via Orchestrator | quality |
| /api/studio/agents/:id/versions | GET | immutable versions + source state | AgentStore | versions |
| /api/studio/agents/:id/releases | POST | approval-gated release request | CP / AgentStore | versions |
| /api/studio/agents/:id/rollbacks | POST | authorized rollback command | CP / AgentStore | versions |
| /api/studio/charts/:chartId | GET | trusted aggregated chart series | domain query adapter | analytics / Ops |
| /api/studio/ops/:module | GET | per-module safe page & status | each owner service | 15 Ops panels |
| /api/studio/ops/actions/:actionId | POST | reauthorized typed operator command | owner service | allowed Ops mutations |
| /api/studio/bilateral/scenarios | POST/GET | create/inspect consent-scoped scenario | bilateral Orchestrator | A2A Lab |
| /api/studio/bilateral/scenarios/:id/invitations | POST | expiring invitation | IAM/consent | bilateral |
| /api/studio/bilateral/scenarios/:id/consent | POST | each tenant's own consent | IAM/consent | bilateral |
| /api/studio/bilateral/scenarios/:id/evaluations | GET/POST | own and shared authorized evidence | bilateral Evaluation | bilateral |

All routes are **proposed; not all are implemented upstream**. The operator command route is a *routing convention*, not a generic unrestricted "execute anything" endpoint. Each action requires a per-action strict schema and owner-service policy; permit only explicitly registered actions, otherwise deny.

## 4. UX-owned canonical action → authority → result

| UI action | Intent and idempotency | Evidence to display | Failure / recovery |
| --- | --- | --- | --- |
| Save draft | optimistic revision/ETag; draft only | new revision | 409 save conflict with preserve/rebase |
| Upload attachment | signed temporary scope + checksum | hash, parser status, rights and provenance | per-file retry, no duplicate rights bypass |
| Validate task | deterministic preflight, safe repeat | unmet conditions, owner-approved requirements | missing cases -> required_action |
| Mark READY | exactly immutable snapshot, explicit owner | snapshot digest & accepted rev | stale revision -> new validation |
| Start build | idempotency per tenant/snapshot/key | workflow receipt 202 and server state | retry lookup by key, never blind duplicate |
| Sandbox run | run request key and side-effect policy | run_id, artifact and trace | no irreversible effect without approval |
| Request Evaluation | existing signed runtime evidence | independent result and case counts | missing gold/signature is BLOCKED |
| Request optimization | bounded attempts/budget; pinned baseline | candidate spec diff; independent retest | no upgrade from mock GEPA |
| Request release | signed gate, approval and deploy target | source-owned release record | 403/409, no optimistic RELEASED |
| Rollback | target pinned version + permission | source-owned transition and deployment state | manual reconcile and incident alert |
| Invite company B | expiring consent invitation with disclosure | invitation status, no private BTP leak | expiry/revoke sends blocked reason |
| Run bilateral eval | both consents, agent digests frozen | signed A/B + joint result | partner offline or no consent blocks |
| Operate registry | maker/checker, different principals | approved/revoked manifest digest | unauthorized no-op; typed denial |

## 5. Source staleness, async and caching

- First iteration: poll active workflow GET every 3–5 seconds while visible, back off on 429/5xx with jitter; stop after terminal state; refetch on focus. Shared SSE can be added later behind exactly the same read model, *not* a P0 dependency.
- Display occurred_at and sourceAsOf and distinguish processing from loading; never compute synthetic progress percent.
- Query cache partitioned by workspace, environment, user visibility profile, entity ID and spec version; revoke on logout/tenant switch. Protected responses default private/no-store.
- Resolve 202 acceptance by operation/workflow identifier after network loss; never submit a new irreversible action just because the response was lost.
- Domain source remains authoritative over UI event order and optimistic updates. Unknown backend enum => UNKNOWN_UNSUPPORTED_VERSION with disabled privileged actions.
- For partial Overview, per-source stamp may be UNAVAILABLE or PARTIAL; aggregate cost/success only from complete source denominators.
- Page links preserve selected filters, current run identity, permitted workspace context; direct URL requires fresh auth.

## 6. ChartKit contract (mandatory; independent of graphics engine)

~~~ts
// I00 contract resolution after A02 Draft PR #19 review. Exactly 15 logical
// templates; variant subtypes do not increase the template count.
// Source types: apps/studio/src/contracts/charts.ts (current C0-prep).
export type ChartKind =
  | "trend" | "stacked_bar" | "horizontal_bar" | "scatter" | "heatmap"
  | "funnel" | "timeline" | "waterfall" | "sankey" | "treemap"
  | "distribution" | "gauge" | "dependency" | "donut" | "a2a_sequence";
export interface ChartSpec {
  chartId: string;
  chartKind: ChartKind; // payload must match; line/area etc are variants
  schemaVersion: string;
  titleKey: string;
  sourceRefs: readonly string[];
  window: {from: string; to: string; timezone: string; granularity: string};
  unit: string;
  currency?: string | null;
  sampleCount: number | null;
  denominator?: number | null;
  completeness: SourceState;
  sourceAsOf: string | null;
  lastObservedAt: string | null;
  revision: string | null;
  redactionLevel: "PUBLIC" | "TENANT" | "OPERATOR_REDACTED";
  tableDataAvailable: boolean;
}
~~~

Actual implementation must use per-type validated schemas rather than this abstract union. Each chart must have a tabular equivalent, source label, time range, sample size, empty/partial/errors, safe hover details, and be unavailable when source not verified. The 15 required templates appear in STUDIO_BOXED_PRODUCT_FEATURES.md. Prefer one typed Apache ECharts adapter; no feature-level direct chart engine imports or duplicated chart palettes. Scalable BFF aggregations, not browser-side 100k raw spans.

## 7. Parallel-agent contract freeze and change requests

**Shared contract editing LOCKED to Integrator/Platform only:** service-owned Java/Python OpenAPI, docs/parallel/CONTRACTS_V0.md, this file, apps/studio/package.json, app root layouts, src/server/** and src/shared/api/**. Feature agents only consume these types using modules' public exports and supply adapter expectations as REQUEST files inside their exclusive feature folders.

Contract change proposal format:
- owner-agent ID and source feature;
- exact old/new JSON request+response and safe runtime validation;
- impacted screens, services, routes and source-of-truth;
- breaking/backward compatible classification and schema version;
- security, tenant and hidden gold impact;
- test diff and migration sequence;
- request integration owner sign-off BEFORE touching common contract.

No feature agent can add a new global backend route or modify a shared enum by itself.

## 8. Executable acceptance inventory for integrator

These are tests to create and run, NOT assertions that tests currently pass:

| Test ID | Journey / failure | Expected evidence |
| --- | --- | --- |
| CJM-E2E-001 | RFQ wizard with real tenant files and scopes → READY → build → sandbox output | real output file + immutable snapshot + trace |
| CJM-E2E-002 | certificate verification through same code with different BTP/tools | independently accepted discrepancy report |
| CJM-E2E-003 | safe Eval FAIL → bounded GEPARD candidate → independent re-evaluation | pinned baseline/candidate and exact signed report |
| CJM-E2E-004 | impossible case / missing external receipt | BLOCKED, never PASS or RELEASED |
| CJM-E2E-005 | user missing Registry permission, request admin grant | no implicit grant or unauthorized tool use |
| CJM-E2E-006 | two-tenant deep links, search, cache, run artifact, chart, SSE/poll | no foreign data / existence leak |
| CJM-E2E-007 | draft autosave conflict/refresh/file upload failure | no lost input, safe revision and retry |
| CJM-E2E-008 | duplicate Start Build and lost HTTP 202 | idempotency results in one workflow |
| CJM-E2E-009 | evaluator outage/unknown status | INCONCLUSIVE/UNAVAILABLE, never fake green |
| CJM-E2E-010 | released version is stale, owner approval denied | 403/409, no browser-only release |
| CJM-E2E-011 | approved rollback, user denied rollback | authoritative rollback with audit; forbidden mutation remains blocked |
| CJM-E2E-012 | 15 Ops sections and role-specific routes | authorized screens, correct unavailable source states, 403 for wrong roles |
| CJM-E2E-013 | 15 ChartKit variants with real and missing fixtures | accessible table, provenance, no fabricated data |
| CJM-E2E-014 | bilateral missing B consent / revoked consent / partner offline | blocked, redacted history and separate tenant audit |
| CJM-E2E-015 | bilateral A0×B0, A1×B0, A0×B1, A1×B1 | version pinning, independent A/B and joint results |
| CJM-E2E-016 | large run trace, pagination, responsive inspector | bounded payload, accessible table / UI usable |
| CJM-E2E-017 | idea-only editor/microfrontends | no working editor/deployment buttons or spurious API calls |
| CJM-E2E-018 | role revoked mid-session, tenant switch | permission refetch, protected caches cleared |
| CJM-E2E-019 | model usage absent or out of sync | no fabricated cost/per-success chart |
| CJM-E2E-020 | operator tries unsafe retry, replay or raw secret access | server refuses, actor/action audit |
| CJM-E2E-021 | failed Builder after authorized READY | timeline truthful after refresh and retry only when safe |
| CJM-E2E-022 | offline/reconnect/late event | last verified state + safe reconciliation |
| CJM-E2E-023 | accessibility and RU/EN critical keyboard workflows | focus, contrast, labels and screen reader alerts |
| CJM-E2E-024 | release gates on mock-only GEPARD / unsigned evidence | cannot promote candidate |

**Data fixtures:** synthetic RFQ and certificate examples only; different tenant key/secret fixtures; known bad prompts, missing tools, corrupted attachments, hard veto cases, fake external receipt, offline provider. Every test includes exact commit SHA, test command, run URL/log, dataset version, actual outcome and remaining limitations.

## 9. Definition of Ready vs Definition of Done

**Agent task READY:** frozen contract version + route ownership + typed fixture + expected statuses + permissions + accessibility/error copy + tests + known backend mock/live boundary.  
**UI unit DONE:** implementation paths isolated, type/lint/unit/component tests executed; screenshot evidence for states; no secrets/fake data.  
**Integrated DONE:** owner-approved API version exists and real service wiring on pinned SHA, integration E2E passes with tenant/auth negative cases and role checks.  
**Production DONE:** service deployment, IAM/key/effect receipts, operational telemetry/rollback and independent owner approval evidenced; neither PR status nor demo UI is enough.