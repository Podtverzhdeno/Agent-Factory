# Proposed microservice decomposition — ASSISTANT DRAFT

> This is an advisory proposal for @Podtverzhdeno to review, not an approved owner architecture.
> Owner-provided facts: OWNER_INPUTS_2026-10-27.md. ADR: adr/0002-microservices.md.

## Logical separation

Control plane manages creation, policy, contracts, optimization and release. Data plane runs released customer agents in scoped execution containers. Evaluation and optimization are independent from the candidate agent.

| Deployable | Language | Responsibility | Deployment proposal |
| --- | --- | --- | --- |
| factory-orchestrator | Java Spring Boot | build lifecycle, coordination, release approvals, budgets, state machine and audit | independently scalable control-plane |
| tool-mcp-registry | Java Spring Boot | approved capability manifests, schemas, permissions, dependencies, versions and safety classification | independently scalable control-plane |
| agent-builder | Python | minimum tool selection and immutable AgentSpec + container provisioning | worker / independently scalable |
| agent-runtime | Python + durable adapter | configured harness, selected tools/MCP, model calls, state, A2A endpoint | reusable single runtime image, one isolated container per agent initially |
| evaluation | Python | independent test datasets, business outcome validators, regression reports and failure taxonomy | independently scalable async workers |
| gepard-optimizer | Python | prompt/harness/tool-config optimization and experiment management; NEVER bypasses release gate | independent async service |
| soup-trainer | Python/GPU | optional approved dataset fine-tuning and model artifact production | separate optional service, not MVP critical path |

A2A ingress can initially use a standard reverse proxy/API gateway routing authorized endpoints to Python A2A SDK served by each agent container. No bespoke A2A microservice required at MVP.

## Data ownership (owner mandates separate databases)

Each service owns an independent database, user/role and migrations. For initial cost control, multiple logical PostgreSQL databases can share a physical server or managed cluster; other services must use APIs/events, not read each other's tables. Object storage is used for immutable AgentSpec/build artifacts and dataset versions; Langfuse maintains its own supported backing store.

## Communication proposal — owner has not finalized REST/Kafka

REST/OpenAPI for commands and query responses (task creation, tool registry lookup, approvals, build status). Kafka for asynchronous stage transitions, long evaluations and optimizer work, e.g. build.requested -> agent.assembled -> evaluation.completed -> optimization.requested -> evaluation.completed -> release.ready.

Use correlation IDs, schema versions, backoff/DLQ, persisted orchestration state, transactional outbox and idempotent consumers. Kafka does not replace the durable build state machine or guarantee exactly-once non-Kafka external writes. A2A should expose protocol-compliant HTTP/JSON-RPC independently of internal Kafka.

## Pi Durable — special architecture issue

Published Pi Durable is an EXPERIMENTAL TypeScript/Node package, not a Python library. Factory-level inclusion means builder provisions a durable-capable runtime for the generated agent; it does NOT mean running Pi inside the Java control-plane Orchestrator.

**MVP RUNTIME CHOICE CONFIRMED IN CHAT (owner): option A — Python Agent Runtime + LangGraph/PostgreSQL checkpoints. Pi Durable is a separate experimental PoC, not in the MVP critical path; it does not actually run within the chosen Python harness.**
PoC option B: Node/TypeScript Pi Durable harness invokes Python domain tools via authenticated local HTTP/MCP/gRPC and persists workflow state. Aligns with Pi Durable feature but increases language/runtime overhead.
PoC option C: combined Python+Node agent container with explicit IPC and failure ownership; requires proof that restart semantics and external side-effects are correct.

Owner chose A for MVP. The complete service topology and ADR still require GitHub-based owner ratification; durable safety still needs crash/restart, duplicated tool-effect, timeout, cost and operational benchmark. Durable state alone is not a guarantee of exactly-once ERP writes.

## Complementary stack proposals

PostgreSQL; Java Spring Security or managed identity provider; OpenTelemetry Collector for Java/Python end-to-end traces; Langfuse for LLM-specific traces/experiments; Prometheus/Grafana for platform metrics; S3-compatible object storage; managed secrets vault; **no LiteLLM proxy required for the single-provider MVP**: use a typed Python ModelGateway adapter first. Consider LiteLLM Python SDK or gateway only after multiple providers, centralized spend caps, virtual keys or automated routing justify its cost and operational complexity; optional Redis/vector index only on evidence of need.

## Environment

Proposed local MVP deployment: Docker Compose for integrated stack; preserve container images and Helm/Kubernetes-compatible contracts so scale-out is possible later. Kubernetes itself is not owner-approved. No customer on-prem deployment at MVP.

## Risks / trade-offs to discuss

Six main independently deployed components may be costly for a very small team; split only on ownership and scaling needs. Per-agent container resource overhead may require pooling later. Kafka and observability increase pilot operation costs. GEPARD must have fixed baseline and independent holdout; no direct untested production changes.

## Approval

This advisory document remains DRAFT. The owner must decide topology and sign ADR-0002 through a real GitHub action.