# Design: Studio CJM, parallel ownership and integration

**Status: proposed logical UI design. Not a service topology ADR.**

## Containers and data authority

1. React/Next.js+strict TypeScript/SCSS Modules modular Studio application; customer views and authorized Operator Console share domain references.
2. Server-only Studio BFF authenticates OIDC/CSRF, resolves workspace/environment, checks actor scopes, makes typed calls to Orchestrator, Task Intake, Registry, Builder/Runtime/Eval read adapters, LiteLLM, AgentStore, artifact management and observability projections. BFF does not own business policy/release correctness.
3. Workflow and task statuses always come from source-owned backend; stable read models contain source, timestamp, revision, completeness and allowed actions.
4. Initial active-page polling is sufficient; SSE can be added later via same projection/reconciliation contract. Keep provider keys, signing keys, hidden gold and private traces off browser/cache.
5. Source capability availability is computed by the server from deployed integration health, actual evidence, actor/tenant grant and environment; static checked-in feature catalog is design intent only.

## Navigation and responsibilities

- Client: Agents/Overview → Create Agent (Task Intake wizard) → Workflow → Run/Playground → Quality/Candidates/Versions → controlled release → Monitoring/Analytics.
- Operator: 15 mandatory routes, divided into three non-overlapping teams of five, each behind verified privileged permission. No shared route or data ownership is implied by UI proximity.
- Advanced bilateral mode: A/B privately scoped BTP+AgentSpecs and consent; shared A2A only with allowed disclosure; independent A and B gold and joint evaluation; separate approvals.
- Charts: shared typed adapter + validated source data. Chart engine choice is implementation-level pending bundle/performance check; product design contains 15 templates.
- Idea-only: future editable LangGraph graph IR/compiler and microfrontend decomposition. No create/edit/deploy actions for these in current implementation.

## Contracts and concurrency

See docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md for frozen proposed Studio DTOs/routes/error semantics. Feature teams write modules against fixed client interfaces/fixtures, never directly edit service OpenAPI or src/server. Integrator owns changes to public contract, Next root/layout/package manifests, e2e and final merged revision. Mandatory request revision/ETag, command idempotency and exact typed error; no optimistic RELEASED/PASSED.

## Ownership boundary

All coding agents begin from **same pinned commit** and create distinct branches. Disjoint owned files only; one work packet = one PR. Each controls only local implementation and test files in its feature paths. Separate integration owner performs schema/codegen shared updates, routes composition, app/bootstrap dependencies and central e2e. No agent can merge to main or ratify ADR. No direct edits to docs/parallel/CONTRACTS_V0.md, ADR, openspec common files or root manifests by feature agents.

## Safety/failure design

- Tenant/role permissions checked at BFF + owner service, including files/chart data/SSE search and direct URLs.
- Unsafe operation effects require real external receipt, not just reservation key. Missing evidence blocks Evaluation/release.
- Unknown status and unsupported schema degrade safely.
- Async 202 command receipt tracked by workflow/run ID even if HTTP response lost; no duplicate re-submission.
- Source outage yields last known timestamp + unavailable, not zero metrics.
- Shared partner history never exposes internal prompt/holdout/private tool logs.

## Rollout / failure recovery

Design-only → isolated feature tests with synthetic fixtures → single integrated branch lint/contract Playwright → backed staging service integration with security/negative tests → owner-approved pilot with safe release/rollback. Browser route or component failure must not release an agent. Feature flags can hide unready actions but do not confer permission. Roll back frontend without changing source-owned backend state.

## Risks and owner decisions

ADR-0002 still pending owner authorizing service topology, Task Intake ownership, deployed BFF boundary, IAM source and production hosting. No new mandatory backend deployable is approved by this doc. Customer-installable on-prem "box" is NOT decided merely by using the term boxed product. Full Operator Console design and charts are mandatory target scope; avoid assuming their upstream APIs are ready.
