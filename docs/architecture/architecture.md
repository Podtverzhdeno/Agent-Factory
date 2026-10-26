# Architecture: verified, minimal, self-optimizing agent factory

Status: PROPOSED.

## Diagram
BusinessTask → Analyze → Registry capability matching → AgentSpec Compiler → Sandbox Agent Runner → Independent Evaluator → Repair Controller → Quality Gate → Release Artifact → A2A adapter.

Feedback: Evaluator findings → choose permitted repair → reassemble candidate → rerun independent tests. Stop on pass, BLOCKED, spend or attempt cap. Do not let LLM decide its own success.

## Bounded contexts
- Domain: typed BusinessTask, ToolManifest, AgentSpec, Evaluation, Policy and Release contracts.
- Application: analyze, select, assemble, execute, diagnose, optimize, approve, release.
- Infrastructure: Postgres metadata/audit, immutable artifacts, LLM gateway, sandbox, evaluator datasets, Langfuse.
- Adapters: MCP/REST/Python tools, official A2A SDK, GEPARD, durable runtime (LangGraph/DB, Pi Durable research adapter), optional Soup/LoRA.

Dependencies MUST point towards domain; the domain cannot import LangGraph/Pi/LLM SDK/MCP SDK.

## Core contracts
BusinessTask: tenant, objective, typed inputs/outputs, acceptance assertions, allowed effects, resource budget, data rights.
ToolManifest: tool id/version, transport, input/output JSON schema, capabilities, side-effect classification, tenant scopes, trust/owner, fixture tests and dependencies.
AgentSpec: immutable digest of objective, selected tools/versions, grants, model, prompt, harness, workflow, checkpoint policy, A2A interface and evaluator version.
EvaluationRun: candidate/baseline/dataset version, independent score, safety violations, failure taxonomy, trace/artifact references, latency and cost.
ReleaseRecord: approval, gates, provenance, rollback target and audit.

## Security and durability
Model-generated plans are untrusted. Policy gateway enforces tool permissions, not the prompt. Tenant-specific credentials injected at execution, never in repository/prompts/traces. SSRF/network egress allowlist and sandbox for external tools. Consequential external effects require idempotency and reconciliation; durable checkpoints do NOT guarantee exactly-once ERP actions.

## Candidate stack
Python 3.12+, FastAPI, Pydantic, PostgreSQL, SQLAlchemy/Alembic, pytest/Ruff/Pyright; Langfuse for tracing; official A2A SDK; GEPARD optimizer port. Durable runtime PoC compares LangGraph+Postgres against Pi Durable. These are candidates, not installed components.

## State machine
DRAFT → ANALYZED → ASSEMBLED → RUNNING → EVALUATING → REPAIRING (bounded loop) → APPROVAL_PENDING → VERIFIED → RELEASED → MONITORED. Exceptional: FAILED, BLOCKED, ROLLED_BACK. Guards protect every transition.
