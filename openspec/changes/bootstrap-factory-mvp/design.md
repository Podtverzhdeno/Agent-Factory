# DRAFT — logical design only; owner microservice topology is pending

Owner choice: microservices. Functions described below are NOT a deployment map or approved service boundaries. Ask questions in docs/architecture/OWNER_QUESTIONNAIRE.md; follow owner-approved ADR-0002 before implementing services.

# Design — initial verified agent factory

## Logical architecture

1. Intake API: BusinessTask {task_id, tenant_id, objective, input_contract, output_contract, dataset_refs, success_criteria, constraints, allowed_effects, budget}.
2. Task Analyzer: derives required capabilities and measurable acceptance tests; never silently invents permissions or claims missing data exist.
3. Capability Registry: pinned, typed ToolManifest {tool_id, version, transport, input/output schema, capabilities, risk_level, side_effects, scopes, owner, health, fixture_tests, approval_policy}.
4. Planner/Assembler: deterministic minimal set-cover + capability compatibility rules; LLM may propose candidates, deterministic policy decides eligibility. Emits immutable AgentSpec with model/prompt/tool versions, grants and A2A metadata.
5. Sandbox Runtime: isolates tenant, secrets, outgoing requests and action permissions; executes agent with budget and max-step limits. A2A is an adapter, not embedded in domain logic.
6. Eval & Diagnosis: checks deterministic invariants before model-based judges. Scores correctness, tool usage, evidence, latency, cost and safety; persists trace, dataset version and candidate ID.
7. Repair Controller: diagnose cause; choose bounded action: revise prompt, choose alternative approved tool, alter retrieval/config/workflow or require a human. GEPARD is a pluggable optimizer; no untrusted code execution as an unrestricted repair action.
8. Durable Port: checkpoint, resume, retry and timeout; compare LangGraph/Postgres with Pi Durable/other implementation via fault injection. Side effects protected by idempotency keys and reconciliation.
9. Release Manager: immutable artifacts, independent hidden holdout, human approval for risky effects, signed provenance record, rollback.
10. Optional Training Port: Soup/LoRA only for licensed, sufficiently sized datasets and demonstrable gain per correctly completed task.

## Corrected service interaction sequence (explicit owner feedback)

1. Orchestrator issues an explicit authenticated REST command to Agent Builder (`POST /internal/builds` with version, idempotency key and budget), persists its running state and awaits an async completion signal. Kafka records completion/failure events; an event itself does not decide the next build.
2. Builder selects approved capabilities and creates immutable AgentSpec. A candidate Agent Runtime is provisioned using the common Python/LangGraph runtime image.
3. Orchestrator requests Evaluation on candidate runtime with fixed tests. Evaluation produces outcome, traces, error taxonomy and independent checks; Orchestrator decides next phase.
4. Orchestrator invokes GEPARD with agent/version ID, current prompt/harness and evaluation evidence. GEPARD directly interacts with Agent Runtime or versioned AgentSpec via read-only authorized interface, proposes optimizations and evaluates trial candidates in sandbox. It does NOT directly overwrite an active production instance. Orchestrator schedules independent re-evaluation and automatically rolls out passing low-risk changes through controlled version promotion.
5. If a specialization request exists OR evidence indicates model-level limitations after other repairs, Orchestrator directly invokes optional Soup Training, independent of GEPARD. Any model artifact receives a new immutable version and requires re-evaluation before release.
6. After passing release gates and required approvals, Orchestrator publishes the version and exposes authorized A2A. Kafka carries lifecycle events with correlation IDs; REST invokes operations explicitly.

## Model Gateway — LiteLLM (owner-selected)

Factory-provisioned agents and GEPARD use a typed ModelGateway backed by a shared LiteLLM Proxy. Registry policy pins allowed models per AgentSpec; the gateway controls provider credentials, tenant/agent budgets, quotas, routing and usage observability. A proxy database must be configured for persistent spend controls. The gateway is not a business evaluator and cannot approve agent releases. The owner has not yet ratified concrete microservice boundaries, credentials and deployment in ADR-0002.

## Domain ports (framework-independent)

TaskRepository, RegistryPort, ModelGateway, AgentRunner, EvaluationPort, TraceSink, OptimizerPort, CheckpointStore, ReleaseRepository, CredentialProvider, ApprovalService and A2ATransport. Domain only depends on contract types.

## State machine

DRAFT → ANALYZED → ASSEMBLED → RUNNING → EVALUATING → (REPAIRING → ASSEMBLED) | (APPROVAL_PENDING → VERIFIED) | FAILED | BLOCKED. VERIFIED → RELEASED → MONITORED; any regression → ROLLED_BACK. Explicit max_attempts, token/spend/time caps, anti-loop and terminal reasons.

## Data entities

BusinessTask, DatasetVersion, CapabilityManifest, CredentialReference (never secret value), AgentSpecVersion, EvaluationRun, Finding, RepairAttempt, Approval, Release, TraceReference and AuditEvent. PostgreSQL for metadata/event audit. Object storage for artifacts; tenant-bound keys and retention policy.

## MVP API contracts (proposed, not implemented)

- POST /v1/tasks — validate task input (202 + task id)
- POST /v1/builds — launch authorized build (202 + build id)
- GET /v1/builds/{id} — status, blockers, selected tools, budget consumption
- GET /v1/builds/{id}/evaluations — evidence, scores, failures
- POST /v1/builds/{id}/approve — approved actor only
- POST /v1/builds/{id}/release — gated action
- GET /.well-known/agent-card.json — optional A2A adapter metadata for released agent
- A2A Task handling — separate transport adapter using official SDK and protected identity

## Test harness: proof before confidence

Gold task set + disjoint tune/validation/hidden holdout; deterministic stubs for external tools; fault injection; malicious tool description cases; unauthorized action cases; multi-tenant leakage checks. Pin evaluation dataset and grader versions. Any critical safety defect blocks release regardless of aggregate score.

## Failure and optimization decision table

- Wrong format → schema/typed decoding correction first; GEPARD only if needed.
- Wrong tool selected → registry capability disambiguation, eligible alternative or new approval.
- Correct tools but wrong sequencing → modify plan/harness; validate side effects.
- Missing evidence/data/rights → BLOCKED + human request; never hallucinate connector.
- Long-running process interrupted → durable resume; test idempotent external effect.
- Repeat model semantic errors → compare GEPARD and model alternatives before Soup/LoRA.
- Excessive expense → cheaper model or retrieval strategy subject to quality gates.

## Trust model and deployment boundary

Factory control plane never receives arbitrary client production admin credentials. Tool adapters enforce allowlisted endpoints, declared side effects, tenant-scoped grants, SSRF resistance and outbound network restrictions. Running customer agents is a data plane; separate tenants for traces and data. Generated executable code disabled for MVP unless explicitly reviewed/sandboxed. Model outputs are untrusted.

## Alternatives

LangGraph checkpointing vs Pi Durable vs Temporal: run comparable interruption and throughput tests before selection. For MVP prefer Python native path; Pi durable as research adapter, not committed foundation. OpenSpec canonical specifications; Spec Kit review methods avoid duplicate plan sources.

## Rollout

Local synthetic cases → curated consenting datasets → shadow pilot (no live writes) → approved pilot → production only after independent security and customer signoff. Rollback reverts AgentSpec/Tool versions without destroying audit history.
