# A07 pre-C0 research report — Operator Console modules 1–5

**Date:** 2026-10-28  
**Task:** STU-T09 / GitHub Issue #14  
**Phase:** PRE-C0 RESEARCH ONLY — implementation blocked  
**Source ref inspected:** `research/a02-pre-c0-design-charts-20261028`  
**Inspected ref HEAD:** `6dd002fc0cb9dffd11d3706e830c768d8479f705`  
**This report is not a task claim, lease, implementation, or production-readiness assertion.**

## 1. Gate decision: BLOCKED

- Issue #14 is `BACKLOG / WAITING_FOR_C0`; `current_owner=null`, `claim_generation=0`, and claim/progress timestamps are null.
- Issue #18 says the atomic claim/stale-check/takeover coordinator is not deployed. An issue assignee or comment is not a lease.
- `apps/studio` on the inspected research ref contains `src/features/chart-showcase` and `src/shared`, but no `package.json`, `tsconfig.json`, `app/layout.tsx`, or Ops feature directory was found. The repository's top-level `services/` directory is also absent on this ref.
- Consequently, there is no verifiable frozen C0 SHA, runnable frontend toolchain, public `@studio/*` exports, or confirmed Ops API contract in the inspected state.
- ADR-0002 remains owner-pending. This work does not decide or implement service topology.

**Decision:** do not implement route/UI code, install dependencies, claim Issue #14, or assert tests passed. Resume implementation only after I00 publishes a frozen C0 SHA/contracts and a trusted coordinator grants a generation-fenced lease.

## 2. Five module data/API readiness matrices

“NOT VERIFIED” means no authoritative endpoint/schema or live service evidence was confirmed from the inspected ref and task packet. It does not prove that no service exists elsewhere.

| Module | Required source / authoritative objects | Proposed page contract | Actions / safety | Current evidence |
|---|---|---|---|---|
| Fleet `/ops/fleet` | Deployment provider/service registry; instance, deployment/version, region, readiness, resource/capacity, incident reference, source timestamp | Search; environment/region/status filters; paginated service/instance table; columns: service, instance, version, region, readiness, last verified, source-as-of; deep link to incident/deployment | Read-only initially. Restart/scale only if a documented privileged API, capability and audited confirmation exist. No uptime/SLA inferred from missing samples. | Deployment provider/API and real health snapshot NOT VERIFIED. |
| Workflows & Queues `/ops/workflows` | Control Plane workflow/jobs; command outbox, event inbox, broker/queue and DLQ only if deployed; attempt/idempotency/correlation IDs | Status/time/tenant-safe filters; workflow/job table; transition/attempt timeline; age and last-source timestamp; drill-down by workflow/run/trace ID | Retry/replay only via authorized idempotent command API with deduplication and audit. Never expose retry when source/action contract is missing. No Kafka lag shown as 0 when broker/metrics unavailable. | Workflow/queue API and broker deployment/metrics NOT VERIFIED. |
| Builder / AgentSpecs `/ops/builder` | Builder service and immutable AgentSpec store; build ID, spec digest/revision, tool versions, validation reasons, authorized diff | Build status/search; spec digest/revision; selected tool IDs/scopes; validation result/reason; access-controlled prompt/harness diff; deep link to spec/run | Read-only until APIs are confirmed. No raw secrets, hidden evaluation gold, or cross-tenant prompt/spec access. Invalid build reason must come from source. | Builder API and immutable spec read contract NOT VERIFIED. |
| Runtime & Checkpoints `/ops/runtime` | Runtime/orchestrator run, pinned tenant+agent version, checkpoint/restart metadata, effect receipts, memory boundary | Filter by run/status/agent/version/time; run table and timeline; checkpoint lineage, source-as-of, link to Run Inspector | Resume/restart only with backend-enforced tenant/version authorization, checkpoint validation, idempotency and audit. Never promise exactly-once external effects without verified receipt/reconciliation. | Runtime/checkpoint API and deployed durable semantics NOT VERIFIED. |
| Tool/MCP Registry `/ops/registry` | Registry manifest/version, scopes, capability grants, approval records, revocation and audit log | Search/filter by tool, status, owner, version and scope; manifest detail; approval/revocation history; impact and denial reasons | Maker-checker approval and revoke must be server-authorized and audited. No approval/revoke controls until backend capability and permission checks are confirmed; frontend visibility is not authorization. | Registry API, lifecycle and approval contract NOT VERIFIED. |

## 3. Common UI state and provenance contract

Every page should distinguish these states rather than turn unavailable data into healthy/empty data:

- **Loading:** explicit pending state; do not show placeholder metrics as real.
- **Empty:** source connected, authorized request succeeded, and the source explicitly returned zero rows.
- **Not connected / unsupported:** source or endpoint is not deployed or not configured; show the exact missing dependency and source status.
- **Forbidden:** authoritative 401/403 or capability denial; do not leak row counts or hidden resource names.
- **Partial:** some sources failed or fields are incomplete; identify which source/fields are missing.
- **Stale/degraded:** display source timestamp and staleness reason when supplied; do not silently treat stale snapshots as current.
- **Error:** preserve correlation/request ID when safe; distinguish retryable read failures from rejected commands.

For every real dataset show source identity and `as_of`/observed timestamp where available. Empty data is valid only after a successful authorized source read. Unknown is not zero. `PASSED`, `RELEASED`, health, queue lag and mutation success must come from authoritative services, never frontend inference.

## 4. Access and action policy

1. Operator role is necessary but not sufficient: enforce tenant/environment scope and per-action capability server-side.
2. Default to read-only. Retry, restart, approve, revoke, resume and replay controls remain disabled/absent unless a matching documented API, authorization contract, confirmation policy and audit result are available.
3. A UI-side hidden button is not a security boundary. Capture and test backend 401/403 refusals; do not retry rejected destructive commands automatically.
4. Keep customer Studio workflows separate from privileged operations. Link to customer Run Inspector, spec or artifact using authorized opaque IDs; never duplicate or broaden customer permissions.
5. Paginate server-side, bound filters/sort, and avoid exposing secrets, raw credentials, hidden evaluation data or other tenants' object names.

## 5. Test plan (planned, NOT RUN)

| Test ID | Scenario | Expected acceptance |
|---|---|---|
| A07-STATE-01 | Each module receives loading, successful empty, NOT_CONNECTED, 401/403, 5xx, partial and stale responses | Distinct truthful states; source status/time visible; no false success or zero metrics |
| A07-AUTH-02 | Non-operator, wrong tenant and insufficient capability request each module/action | Server denial respected; no cross-tenant rows or mutation; refusal is observable/auditable |
| A07-FLEET-03 | Fleet provider unavailable or health fields missing | No invented uptime, capacity or healthy status |
| A07-QUEUE-04 | Broker/lag source absent; retry/replay API absent; duplicate command attempted | Lag is unavailable, not zero; actions disabled; no duplicate effect |
| A07-BUILD-05 | Invalid spec, missing digest/tool version, inaccessible prompt diff | Source-provided reason or explicit unknown; no secrets/hidden gold disclosure |
| A07-RUNTIME-06 | Expired/missing checkpoint, mismatched tenant/version, missing external effect receipt | Resume denied or blocked with reason; no exactly-once claim |
| A07-REGISTRY-07 | Approval/revoke without capability, dual approval or audit source | Mutation denied/not offered; no frontend-only approval |
| A07-UX-08 | RU/EN, keyboard-only, screen reader, responsive table and pagination | Accessible labels/focus and locale parity; large result sets stay bounded |
| A07-CONTRACT-09 | Type/API contract and route build on frozen C0 | Strict typecheck and tests run on exact SHA; record command and actual output |

CJM target references: **CJM-E2E-012, 020, 021, 022**. These are targets only; no E2E was run. Typecheck, lint, unit, component, browser, service integration and production checks are all **NOT RUN** because the inspected ref has no confirmed C0 app skeleton/toolchain.

## 6. Requests for I00

1. **C0 freeze:** publish immutable `BASE_SHA`, app root/Next/TypeScript/SCSS/test skeleton, package manager and lockfile, supported Node version, and CI commands.
2. **Typed exports:** publish stable/versioned public `@studio/api`, `@studio/contracts`, `@studio/ui`, `@studio/charts`, and `@studio/auth` contracts, including source stamps, pagination, typed errors, capability projection and action results.
3. **API evidence:** identify authoritative service owner, endpoint/schema, auth/tenant rules, availability status and test fixture for each of the five rows in §2. Explicitly mark unavailable sources.
4. **Action contracts:** specify audit/correlation/idempotency, confirmation, maker-checker and denial semantics for any proposed retry/restart/resume/approve/revoke operation.
5. **Coordinator lease:** deploy/verify serialized authenticated claim coordinator and path/generation CI gate; then grant STU-T09 with owner, generation, server-issued UTC timestamp, branch and C0 base SHA.
6. **Shared dependency requests:** A01 privileged BFF adapter and A02 table/status/chart primitives need published export names and source-state semantics before Ops can consume them.

## 7. Implementation boundary and next step

After all gates pass, create the five owned routes and modules under the exact A07 allowlist only:

- `apps/studio/src/features/ops/core/**`
- `apps/studio/app/[locale]/ops/fleet/**`
- `apps/studio/app/[locale]/ops/workflows/**`
- `apps/studio/app/[locale]/ops/builder/**`
- `apps/studio/app/[locale]/ops/runtime/**`
- `apps/studio/app/[locale]/ops/registry/**`

Do not edit global layouts/navigation, package manifests/lockfile, shared DTOs, OpenSpec, service code, CI or ADR. Put cross-owner requests inside this owned feature directory and route them to I00.

**Current result:** research report and test plan only; no feature implementation, no lease, no PR claiming app code, and no tests executed. Next action is I00 to freeze C0 and enable authorized task claiming.
