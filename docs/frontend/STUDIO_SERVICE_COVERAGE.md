# Agent Factory Studio — complete product / service coverage map

**Status: PROPOSED, 2026-10-28. Owner architecture sign-off remains pending under ADR-0002.**  
**Scope rule:** This is a long-term **coverage inventory**, not a P0 commitment for each microservice to have a page. MVP cutline: [`STUDIO_MVP_SCOPE_DECISION.md`](STUDIO_MVP_SCOPE_DECISION.md).  
**Baseline:** `docs/product/MVP.md`, `docs/architecture/PROPOSED_SERVICE_MAP.md`, `docs/parallel/CONTRACTS_V0.md`.  
**Related:** `AGENT_FACTORY_STUDIO_RFC.md`, `STUDIO_UX_AND_DELIVERY.md`.  
**Scope:** Product/UX contracts and architecture; NOT deployed frontend or integration acceptance.

## 0. Fundamental principles

1. **One product, multiple bounded services.** Studio is a human-friendly projection/orchestration UI; not a new “god-service”, does not own other services' databases and must not independently infer truth.
2. **Primary unit is a verified business operation.** Client buys reliable output and proof, not a canvas of prompt nodes. One specialized B2B agent per task is P0; cross-enterprise pair is an add-on.
3. **One canonical resource graph:** Workspace → BusinessTaskPackage revision → READY TaskSnapshot → Workflow → Build → immutable AgentSpec/version → Evaluation(s)/Optimization(s) → ReleaseRecord/Deployment → AgentRun(s) → business Artifacts/effect receipts. Every screen connects to these IDs; never collapse build run, evaluation run and production run.
4. **Separate control plane / data plane / independent quality.** The Studio only dispatches commands to authorized API endpoints; Runtime executes operations; Evaluation owns independent hidden gold; Orchestrator/AgentStore owns release truth.
5. **All features may be discoverable; not all are available.** UX uses capability discovery and server-computed allowed actions. Capability labels: `LIVE`, `PILOT`, `EXPERIMENTAL`, `NOT_AVAILABLE` from real server state, not hardcoded marketing badges. P0 unavailable features must not be disguised with interactive mock controls in production.
6. **No fictitious telemetry.** Every metric shows timestamp, interval, source, observation completeness and unavailable/insufficient-data state. Business ROI is calculated only against evidenced counterfactual baseline; not arbitrary savings.
7. **Multi-tenant by construction.** Workspace/tenant selected through authenticated authorization; project/agent rights checked on every BFF/API action. No cross-tenant inference through totals, search, deep links, logs or notification counters.
8. **No free-text as evidence.** Real ERP commitment requires external receipt verification. Agent text, local reservation keys, green UI badges and unsourced model confidence are not evidence.
9. **Security/approval not optional UI chrome.** Risk classification, permission grant, policy approval, signer trust and release entitlement are server-side.

## 1. Unified information architecture (do NOT mirror service names in main navigation)

### Global shell

- Workspace switcher (authorized tenant + project), environment (sandbox / production), global command palette/search, create agent, notifications/action inbox, organization, profile.
- Shell state: auth/session, connectivity, whether data is stale, locale/timezone, rights, overall support.
- Left nav: **Overview** · **Agents** · **Activity / Runs** · **Quality & Experiments** · **Integrations** · **Deployments & Releases** · **Analytics** · **Workspace**.
- Right-side action drawer: contextual issues/approvals and AI Business Copilot; drawer should never hijack main navigation.
- Dedicated `/ops` operator shell (not a separate domain model): Health/SLO · Jobs/Queues · Registry Governance · Execution Inspector · Security/Audit · Costs/Usage · Incidents/Deployments.

### Core page routes (proposed)

```text
/w/:workspace/overview
/w/:workspace/agents?status=&owner=&tag=&query=
/w/:workspace/agents/new                     # Business Task wizard
/w/:workspace/tasks/:taskId                   # Editable draft / revisions
/w/:workspace/workflows/:workflowId           # Build/control-plane timeline
/w/:workspace/agents/:agentId/overview
/w/:workspace/agents/:agentId/playground
/w/:workspace/agents/:agentId/runs
/w/:workspace/agents/:agentId/quality
/w/:workspace/agents/:agentId/architecture
/w/:workspace/agents/:agentId/versions
/w/:workspace/agents/:agentId/access
/w/:workspace/runs/:runId                     # One execution timeline + evidence
/w/:workspace/integrations
/w/:workspace/integrations/:connectorId
/w/:workspace/quality/experiments
/w/:workspace/releases
/w/:workspace/analytics
/w/:workspace/settings/members
/w/:workspace/settings/security
/w/:workspace/settings/billing
/ops/fleet /ops/workflows /ops/jobs /ops/registry /ops/traces
/ops/incidents /ops/audit /ops/providers /ops/tenants
```

Main UI nav stays short: tabs and contextual links handle deep functionality.

## 2. Actual microservice/feature → Studio coverage

| Backend service / bounded capability | User-facing feature and owner | Operator / expert panel | Source/command contract & truth | Current assurance / missing |
| --- | --- | --- | --- | --- |
| **Task Intake / Business Task Package** (logical, not approved deployable) | New agent wizard, document roles, examples, process steps, acceptance, clarifications, draft revisions | Intake queue, extraction failures, version/provenance diff, unresolved questions | Proposed `POST /v1/business-tasks`, validate/ready, immutable TaskSnapshot | RFC only: storage, extraction, API & entitlement not implemented end to end |
| **Artifact Ingestion / Object Storage** | Upload XLSX/PDF/DOCX/CSV/JSON/OpenAPI, purpose, sample input/result, output template, parse status, citations | Parsing pipeline, malware/schema checks, object rights, file lineage, retention | Intent-scoped upload, artifact service, status events, short-lived download | Not a deployed product capability |
| **Factory Orchestrator (Java)** | Build timeline; explain WAITING/BLOCKED; bounded repair; release request / rollback; overall budgets | State machine, operation/outbox IDs, retries/leases, policy transitions, queue timelines | Existing proposed `/v1/workflows`, `/{id}/audit`, `/{id}/release`, `/{id}/rollback`, `/{id}/train`; Orchestrator authoritative | Component/proof branch; production orchestrator integrations unproven |
| **Tool/MCP Registry (Java)** | Integrations catalogue, offered/scoped capabilities, missing grants, version/risk and availability, suggested tools | Manifest submit/approve/revoke (maker-checker), provenance, revisions, policies, dependency and health | Proposed `/v0/registry/manifests`, `/select`, `/builder/manifests`, `/audit`; Registry authoritative | Component tests exist; live MCP, production JWT/storage and full Builder interoperability open |
| **Agent Builder (Python)** | "Why these tools?", agent summary, generated plan, steps, model choice, cost cap; build status | Immutable AgentSpec, snapshot, graph, digest, prompt/harness diff, build errors | Proposed `/internal/builds` + Builder result; command from Orchestrator | Component + isolated tests; real orchestration API not fully wired |
| **LangGraph Agent Runtime / durable ledger** | Playground, execution timeline, artifacts, pause/resume/blocked reasons, version and test/prod label | Graph state, checkpoint/restart, tool call, memory provenance, span durations | Runtime authenticated run API, checkpoints and per-run evidence; Runtime authoritative | Agent04 isolated integration proofs; production deployment and persisted customer operation guarantees open |
| **MCP Tool Gateway + policy** | Permissioned tool usage per run; denied actions, external-effect verification | Schema/tenant/tool-pin checks, effect reservations, reconciliation and sandbox egress | Runtime gateway records, independent external receipt verifier; *effect_key is not a receipt* | Validation in component; external ERP proofs not generally available |
| **Official A2A SDK / ingress** | Published Agent Card, approved external callers, invocation history, partner interactions (optional P1) | Agent identity, principal access, failed auth, protocol errors, tenant-side visible partner trace | A2A SDK adapter + ingress with release state and issuer-scoped identity | Isolated SDK tests; production ingress/interop not generally proven |
| **Evaluation Engine (Python)** | Business outcome scorecard, test cases summary, reasons and confidence, regression, side-effect evidence | Sealed holdout firewall, evidence signature, tools/events/memory hard gates, job leases | `/internal/evaluations`, signed Runtime evidence, evaluation result; independent Evaluation authoritative | Real Runtime → signed Ed25519 → Quality isolated E2E, production service IAM/key management open |
| **GEPARD / DSPy optimization** | "Improve agent" with proposed changes, before/after experiment and required re-eval | Tuning/validation partition, budget, candidate diff, optimizer diagnostics | `/internal/optimizations`, candidate artifact; Orchestrator promotes ONLY after independent Evaluation | Bounded mock candidate tested; actual paid DSPy/GEPA not accepted |
| **LiteLLM Proxy / Model Gateway** | Approved model preset, budget limit, usage & cost per successful operation, latency/quality comparison | Tenant/model routes, provider allowlist, fallback/timeout, API key vault, spend reconciliation | LiteLLM gateway records + evaluator benchmark; budget authoritative only when persisted/reconciled | Owner-selected MVP component; real billing/budget persistence not accepted |
| **AgentStore (Control Plane)** | Versions, active release channel, audit, view diff and safe rollback | Immutable version transitions, releases, provenance, rollbacks, approvals | AgentStore `candidate/verified/released/rolled_back` state; single release authority | Java domain implementation; end-to-end release acceptance pending |
| **Langfuse + OTel / metrics** | Limited safe diagnostic view: costs and timeline, no hidden traces | Spans per run, root-cause, LLM trajectory, p95, errors, SLO, queue age | telemetry projection with redaction; never put raw Langfuse admin credentials in browser | Structured logs partially developed; full end-to-end tracing open |
| **Kafka/outbox/event ingest** | Activity stream, notifications, state changes, no duplicated events | Lag, DLQ, outbox retries, inbox dedupe, replay, delivery age | Event projection from trusted owners through BFF; at-least-once semantics | Proposed topology; no production broker E2E accepted |
| **Secrets / identity / policy** | Account/team roles, connector authorization, audit logs, scoped API key creation (if policy approved), data rights | OIDC/IAM, token rotation, key revocation, approval conflicts, tenant break-glass | service-to-service identity, vault and policy engine; never direct UI access to signer secrets | Production identity and vault are missing implementation dependencies |
| **Soup training (optional)** | Advanced model specialization request with rights/consent and a separate decision | Dataset licensing, GPU job, cost cap, model artifact, post-train eval | Explicit Orchestrator `/train`; independent `training.completed` and retest | P2, NOT automatic GEPARD step |
| **Pi Durable research** | Not promoted as production MVP capability | Research-only benchmark comparing Node/Pi to Python-native checkpoints | read-only experiment/PoC tracking, no live runtime switch | R&D; Python + LangGraph/Postgres is selected MVP |
| **Bilaterial A2A evaluation (optional)** | Two-party scenario lab, shared outcome and authorized shared evidence | Distinct principal/tenant boundaries, baseline freeze cross-pair matrices | explicit consent and private per-party evaluation | P1, not required for one-agent MVP |
| **Workspace + commercial capabilities** (new) | Members, roles, budgets, plan, invoices (when commerce exists), support tickets and notification destinations | Tenant onboarding, usage quotas, billing reconciliation, plans, incident/SLA/support tooling | proposed workspace/Billing BFF and dedicated ownership to be decided | Business capabilities NOT in existing service scope; do not invent services or invoices |
| **Deployment operations (Railway initially)** | Production version and environment labels ONLY from release/deployment state, not health of test gate | Service/container health, image digest, regions, resource and rollback events | deployment controller / observability, operator-only with audited access | Test appliance success != customer production readiness |

**Product rule:** services should be mapped to a *domain experience*; do not add a main navigation item for every deployment just because it exists.

## 3. Screen → backing aggregate → permitted actions

| UI route / surface | Business object and upstream | Read model | Commands (server authorization required) |
| --- | --- | --- | --- |
| Overview | Workspace projection | agent count, actionable exceptions, verified operation KPIs, periods, source completeness | create draft, open issue, filter |
| New Agent Wizard | Task Intake + Artifact storage | mutable draft, purpose-tagged files, inferred requirements with owner-approved source refs | save draft, upload, approve interpretations, validate, freeze READY |
| Workflow Live | Orchestrator + Builder + Evaluation + GEPARD | state transitions, step results, blockers, time/spend; separate current task | start build, acknowledge issue, request optimizer/retest only via Orchestrator |
| Agent Mission Control | AgentStore + Runtime + Evaluation | pinned version, capabilities, access, last runs, safety, quality score | sandbox run, review gates, request release, rollback according to policy |
| Playground | Runtime test candidate | text/file input, tool trace, output artifact, execution policy, cost | execute sandbox run; no side effect on production by default |
| Runs | Runtime + audited effects | filtered list & per-run timeline, proof verification status, resource usage | download allowed artifacts; retry only if idempotency safe |
| Quality | Evaluation + GEPARD + LiteLLM | pass/fail/blocked, exact evidence coverage, cost/latency comparisons | request independent eval; propose bounded optimization |
| Integrations | Registry + external credential manager | scopes, health, approved version, provenance, impact on agents | create auth request, owner consent, maker-checker approval/revoke |
| Versions & Release | AgentStore + Orchestrator | immutable diff, independent evidence, risk, approvals | request approval, release verified, rollback authorized |
| Activity & Notifications | outbox projection | event summary, action required, read receipts, cursor | mark read, snooze, assign to actor (workflow ownership required) |
| Ops Fleet/Queues | telemetry + Orchestrator + runtime | deployments, lag, retries, health, rate and SLO | investigate, quarantine, retry safe commands, rollback if authorized |
| Ops Security/Audit | Registry + IAM + Control Plane | privilege changes, signers, anomalies, contract denials | revoke, rotate per security policy, export redacted audit |

## 4. Normalized language vs actual backend states

UI must distinguish separate state machines, never conflate them:

- Task: `DRAFT, UPLOADING, INGESTING, REQUIRES_CLARIFICATION, VALIDATED, READY_FOR_BUILD, SNAPSHOTTED` (**proposed Task Intake RFC**, not existing CP states).
- Workflow (actual proposed CP enum): `DRAFT, READY, BUILDING, TESTING, OPTIMIZING, TRAINING, RE_TESTING, VERIFIED, BLOCKED, RELEASED, ROLLED_BACK`.
- Build: `QUEUED, RUNNING, ASSEMBLED, FAILED, BLOCKED` (proposed).
- Evaluation: `QUEUED, RUNNING, PASSED, FAILED, BLOCKED, INCONCLUSIVE`; `PASSED` is NOT the same as `RELEASED`.
- AgentStore channel: `CANDIDATE, VERIFIED, RELEASED, ROLLED_BACK`.
- RuntimeRun: `QUEUED, RUNNING, WAITING_APPROVAL, COMPLETED, FAILED, BLOCKED, CANCELLED` (UI model PROPOSED; only map fields with supported backend evidence).
- ToolEffect: `NOT_REQUIRED, RESERVED, UNCONFIRMED, CONFIRMED_BY_EXTERNAL_RECEIPT, RECONCILIATION_REQUIRED` (PROPOSED) — never infer external confirmation from a local effect_key.

Displayed stage = server-owned state + last verified event; no client-side production state transitions. Group backend states to human wording without erasing exact underlying state in operator view.

## 5. Service capability contract and feature flags

Every tab/action queries a BFF capability projection:
```json
{
  "workspace_id": "authorized-workspace",
  "features": {
    "task_upload": {"availability": "NOT_AVAILABLE", "reason": "TASK_INTAKE_NOT_CONNECTED"},
    "runtime_playground": {"availability": "PILOT", "environment": "sandbox"},
    "quality_scores": {"availability": "PILOT"},
    "training": {"availability": "EXPERIMENTAL", "requires_owner_approval": true}
  },
  "allowed_actions": ["task:read", "agent:read"],
  "as_of": "server-issued timestamp"
}
```
This is **illustrative**, not a currently supported endpoint or live result. Flags alone do not authorize operations. A 403/409 from a service wins over UI optimism.

## 6. External partner / A2A privacy model

- Each organization can inspect its own message/operation evidence, shared receipt and explicit disclosures, not the partner's private system prompt, memory, internal tool outputs or holdout.
- A2A chat-like view: sent/received messages (redacted), negotiation stage, outcome and correlation; label **synthetic simulation** vs live production clearly.
- Version of each party frozen for bilateral experiment; no global optimization using the partner's proprietary data.
- A2A purchase/payment protocols or real money movements are not first-wave UX or production capabilities.

## 7. Integration risks to resolve before UI release

1. Task Intake/artifact source of truth absent. Without it the wizard is a prototype only.
2. Registry → Builder projection is temporary and operation-version pinning is unresolved.
3. Runtime→Evaluation signed audit demo passed isolated tests; durability, KMS/mTLS and real external receipt remain open.
4. Evaluation → Orchestrator independent evidence mapping and Release still need real cross-service E2E.
5. No general production release, provisioning of per-agent runtime, A2A public exposure, persisted LiteLLM budgets, live GEPA or billing exists yet.
6. Multi-service schema versions, events, service IAM, data residency and tenant retention must be accepted before launch.
7. Physical service map and UI BFF placement await owner ratification of ADR-0002.

**Never label a frontend page ‘fully integrated’ solely because its mock, DTO or SDD workflow passes.**
