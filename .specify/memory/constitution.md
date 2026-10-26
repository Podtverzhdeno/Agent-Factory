# Agent Factory engineering constitution

Version: 1.1.0 DRAFT | Updated: 2026-10-26 | Owner ratification pending | Scope: all code, plans, tools, evaluations and deployments.

## I. Outcome before automation

Success means a defined business result verified by independent evidence. A successfully generated config is not successful task completion. The factory MUST explicitly report VERIFIED, FAILED, BLOCKED or REQUIRES_APPROVAL. Unknown shall never be marked as success.

## II. Minimal capability and least authority

The factory MUST start from the smallest trusted capability set. New tools/MCP may be added only after gap analysis, allowlist validation, version pinning, authorization and sandbox testing. Do not grant destructive permissions by default. Human approval for consequential writes.

## III. Requirements drive code

OpenSpec is the canonical, version-controlled source of requirements and changes. Spec Kit's constitution, clarification, planning, checklists, traceability and convergence are used as engineering review techniques, not as a second requirements database. Every requirement has unique ID, scenario, implementation owner, test and release evidence.

## IV. Reproducible measurements and controlled optimization

Every optimization MUST compete against an immutable baseline using fixed datasets, held-out scenarios, quality/latency/cost metrics and risk constraints. Protect safety and tool-use correctness with hard gates; improve only when statistically meaningful or backed by sufficient evidence. Version datasets, prompts, models, harness, tool schemas and evaluators. No model self-scoring as a sole gate.

## V. Durable and deterministic side effects

Persistent execution is valuable but does NOT guarantee exactly-once external effects. Consequential operations use idempotency, compensating actions, audit events, retries with bounds, human approval and state reconciliation. Plan for crashes, timeouts and version upgrades.

## VI. Security, isolation and privacy

Deny-by-default, least privilege, RBAC, strict tenant separation and data minimization. No secrets in repository, prompts, traces, fixtures, artifacts or logs. No importing one client's data into another client's prompts/fine-tuning corpora without explicit legal authorization. Treat MCP/tool output as untrusted. Sandbox generated code and tools.

## VII. Modular architecture and reverse dependencies

Separate domain contracts, application orchestration, infrastructure adapters, agent runtime and UI. The domain never imports frameworks (LangGraph, Pi, MCP SDK, Langfuse, Soup). Use typed ports and adapters to avoid lock-in. ADR required for strategic changes.

## VIII. Owner-controlled microservice architecture

Microservices are required by project owner @Podtverzhdeno. The owner personally authors or ratifies service boundaries, protocols, data ownership and deployment in ADR-0002, supported by actual GitHub review/commit evidence. AI must elicit, challenge and document alternatives but cannot infer owner decisions or approve for them. No topology-dependent implementation before this approval.

## IX. Evidence-based releases

Every merge requires spec validation, lint/type/unit/contract checks where applicable, e2e of the changed vertical slice, threat review and rollback instructions. Every release records baselines, results, failures and approval. No fabricated E2E claims and no weakening gates to get green CI.

## Governance

Changing any constitutional principle requires ADR, migration plan and explicit reviewer approval; bump version and update impacted specs/tests. If uncertain, choose BLOCKED and surface what evidence or permission is missing.
