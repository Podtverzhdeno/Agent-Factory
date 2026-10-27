# Twin-Agent Harness — DRAFT design

Full discussion: docs/architecture/TWIN_AGENT_HARNESS_RFC.md.

## Sequence
Two independently authorized BTP revisions -> Kafka task.ready notifications -> Orchestrator correlates bilateral workflow -> explicit BuildAgent(A) and BuildAgent(B) commands -> two Python Builder workers with distinct permissions -> AgentSpec A0/B0 with prompts, tools/MCP, ReAct graph, short-term checkpoints, long-term store, LiteLLM route and A2A interface -> two isolated candidate containers -> Orchestrator triggers Evaluation bilateral A2A test -> A/B/joint outcome + trace cause -> GEPARD optimization or model benchmark (Soup directly from Orchestrator only when justified) -> A1/B0, A0/B1, A1/B1 comparisons + holdouts -> independent release into AgentStore and canary/rollback.

## Boundaries
Builder worker pairs share code, not tenant data or identities. Checkpoint state and long-term memory have separate scopes. Tools/MCP Registry stores manifest and risk; runtime policy enforces grants. Evaluation owns holdout and private oracles, not GEPARD or Builder. Kafka carries lifecycle IDs and summaries, never confidential file bytes. AgentStore is a versioned release registry, not yet a decided independent deployable service.

## Model optimization
Model Cost–Quality Benchmark is an Evaluation capability invoked by Orchestrator. LiteLLM provides access, routing and accounting but does not decide quality. Freeze test corpus, A/B versions, prompt, tools, retrieval, memory setup and model policy before comparison. Validate capability compatibility then compare cheaper candidate per graph node, for one party and joint pair. Include p95 latency, fallbacks, retry costs, cost per independently verified successful business operation, and A/B hard constraints. Fail INCONCLUSIVE when test evidence does not establish the specified quality non-inferiority, and never auto-promote an unsafe model.

## Approval
Owners separately authorize release of A and B. Paired agreement may be needed for mutually breaking protocol changes. Follow owner architecture gate and quality release requirements. Full RFC gives detailed failure matrix and open decisions.
