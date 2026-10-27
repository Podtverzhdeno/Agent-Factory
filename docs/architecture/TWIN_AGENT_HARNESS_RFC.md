# RFC: Twin-Agent Factory, Harness Optimization and Model Cost–Quality Benchmark

Status: DRAFT — architecture owner review pending. This is a proposed design, not an implemented platform.

## Owner-defined operating flow

Organization A submits BusinessTaskPackage A and its authorized files/examples; organization B independently submits BusinessTaskPackage B. Their requirements are stored as separate immutable tenant snapshots, then task.ready notifications can be sent to Kafka. Factory Orchestrator associates the two consented requests with a BilateralBuild and explicitly invokes TWO independent Builder jobs (one shared Python Builder codebase scaled to multiple workers). Kafka does not invent requests or coordinate a workflow by itself.

Both Builders analyze only their own data and authorized tool/MCP registry, producing two versioned AgentSpecs and isolated containers. Initial harness includes ReAct-style control flow, tool/MCP permission gateway, LangGraph/PostgreSQL persistence, short-term memory and separate long-term memory store, tracing, A2A task handling, and configured LiteLLM gateway. Pi Durable remains optional R&D; persistence is built in from the first agent version, NOT an optimization added after a failure.

One independent Evaluation run exercises the pair over actual A2A protocol/task artifacts in an isolated sandbox, evaluating A, B and their joint business outcome. Orchestrator attributes failures and starts scoped GEPARD, deterministic harness repair, Model Cost–Quality benchmarking or (exceptionally and directly) Soup training. Each repair yields versioned candidates; Evaluation replays with pinned partner baselines and new holdouts. Only independently accepted versions are published into tenant-scoped AgentStore for ongoing use. No raw partner secrets, private prompts or gold labels are shared.

## Components and boundaries

- Task Intake/Artifact Ingestion: two separate BTP revisions and private artifacts; owner still decides deployment split.
- Factory Orchestrator (Java Spring Boot): explicitly commands Builder A/B, Evaluator, GEPARD, Model Benchmark and optional Soup; tracks persistent state, approvals, budgets and A2A compatibility releases.
- Agent Builder (Python horizontally scaled workers): same versioned code for A and B; compiles distinct tool grants, harness, workflow, memories, AgentSpec.
- Agent Runtime A/B (Python LangGraph): independent tenant-constrained containers, own short-term checkpoints and long-term stores; approved A2A exchanges only.
- Evaluation + A2A Simulation (Python): protocol fidelity, independent tenant A/B and joint business oracles, faults, reproducible datasets, cross-play.
- GEPARD (separate Python optimizer): proposals to prompts and compatible tool descriptions/arguments and model-facing configurations. Do not assume GEPARD optimizes arbitrary application code or every MCP implementation automatically.
- Soup (optional separate training): direct Orchestrator request with licensed, tenant-scoped training corpus and approval. Does not depend on GEPARD.
- LiteLLM Gateway: calls to approved providers, model capabilities, metering, per-tenant budgets, fallback and routing. It does not certify model equivalence.
- AgentStore: proposed version registry for immutable AgentSpec + pinned runtime/model/tool versions, artifacts, evaluation evidence, A2A AgentCard metadata, tenant permissions, compatibility matrix, candidate/released/rolled-back channels. Owner still must decide whether standalone service or Orchestrator bounded context.
- Kafka: IDs, lifecycle/benchmark events with schema/correlation, never raw uploaded files or private conversation content. Commands explicitly initiated by Orchestrator.

## Harness optimization surfaces and evaluation oracles

1. System/developer prompts: GEPARD proposes candidates derived from approved rules/examples; score business correctness, safety and held-out generalization.
2. Tools: model-facing descriptions and argument hints, capability subset/selection, ordering and error handling; measure exact correct tool and arguments, authoritative effect, time and cost. Permission/schema changes require independent approval.
3. MCP: discovery, tool metadata, protocol/schema compatibility, timeout/retry, endpoint health, trust/authority; contract tests and prohibited-operation denials. New untrusted MCP is never installed automatically.
4. ReAct/action graph: choose/observe/act transitions, tool failures, stop conditions, escalation and retry policies; inspect observable graph/tool events, not hidden model reasoning. Detect loops, skipped actions, false final claims.
5. Short-term memory: thread state, summarization/window/retention and checkpoint resume; verify across turns, interruptions, cross-thread boundaries and latency.
6. Long-term memory: extraction/write criteria, retrieval filtering, authority, deduplication, expiry, provenance and deletion; test stale/wrong/other-tenant facts and privacy boundaries.
7. Durable execution (LangGraph/Postgres): checkpoint granularity, timeout/retry/backoff/idempotent tool effects and recovery policy; process-kill and duplicated-write test. Persistence is a foundational feature, not a GEPARD or Soup replacement.
8. RAG/context: chunking, extraction, query reformulation, retrieval, ranking, freshness and citations; recall, hallucinations, groundedness and cost.
9. Graph/workflows: approval/handoff nodes, safe branches, parallel execution, max steps; validate no unauthorized bypass, infinite loop or deadlock.
10. A2A: AgentCard, schema/Artifact format, clarifying questions, data exchange, turn economy, task status and resume; evaluate both private objectives and shared outcome.
11. Model routes: compare models per node/step through LiteLLM; independent quality non-inferiority and full cost per correct business transaction (including retries, cache, tool overhead, network and failure recovery).
12. LLM weights: separately governed Soup/LoRA with lawful data and benchmark, never silently triggered by GEPARD or cross-tenant transcripts.

## Model Cost–Quality Optimization: separate experiment

Baseline records pinned A0/B0 AgentSpecs, baseline model IDs/provider/config, prompt/tool schemas, memory state initialization, dataset, temperature/seeds when supported, retries/fallbacks and pricing snapshot. Use task-stratified and held-out evaluations with different scenarios including long context, wrong/partial tools, non-English business documents, structured output, A2A delayed response, failure injection and adversarial disclosure.

Candidates are allowed LiteLLM models that support required features (tool-calling/JSON schema/context length/residency/privacy/availability). Compare 1) A cheaper model vs B baseline, 2) B cheaper vs A baseline, 3) both cheaper, 4) multi-step routing where complex nodes use stronger model and simple nodes use cheaper model. Run independent test sets with confidence intervals and conservative non-inferiority margins set by owner. Critical policy and safety regressions are absolute vetoes, not soft quality scores.

Decision metric: combined attributable price of successfully completed A2A operation, not only per-million-token headline price. Include failed attempts, expected retries and fallbacks, tools, processing and actual response usage. Rank candidates on Pareto frontier of cost, quality, p95 latency, stability and resilience; choose cheaper candidate only if measured business quality noninferior and policy gates pass. If insufficient sample, report INCONCLUSIVE; do not claim 'no quality loss'.

Orchestrator stores versioned ModelRoutePolicy in AgentSpec and may auto-promote approved low-risk changes only after separate Evaluation holdout/cross-play and rollback readiness. LiteLLM enforces selected model allowlist, authentication and budgets, but is not the deciding quality evaluator. Each tenant owns its own route and can refuse a cost-saving update.

## A2A cross-play anti-overfitting

Compare frozen base A0+B0 with A1+B0, A0+B1, and A1+B1 for each change class (harness or model). Add held-out peer versions or independent non-factory A2A client. One party cannot approve optimization of the other's tenant. No optimization objective may trade away either firm's private hard constraints to improve a joint result.

## Initial milestones

P0: two independently authorized BTPs, two Builder jobs, persisted initial harness, two isolated agents, one A2A protocol run and independent business gold checks.
P1: failing dialogue -> targeted harness repair -> repeated joint tests -> immutable AgentStore publication; add Model Cost–Quality benchmark with at least one independently tested cheaper route or explicit INCONCLUSIVE result. Soup is optional.
P2: broader partner matrix, more providers, online shadow feedback under consent, stronger statistical evidence and performance operations.

## Owner architecture decisions to make

A. Does AgentStore deploy as a separate Java service or as its own module inside Orchestrator?
B. Is the full two-company A2A build/evaluation/release required in MVP acceptance or P1 after single-agent baseline?
C. Which harness configuration surfaces may auto-promote? Can model switches occur automatically within safe capabilities, or is tenant-owner sign-off mandatory?
D. What non-inferiority tolerance and business-side release rules may trade small quality differences for cost?
E. Who authorizes sharing public/sanitized dialogue transcripts, benchmark ownership and retention?
