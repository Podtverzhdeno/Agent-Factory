# Change: twin-agent-harness

## Why
A bilateral A2A business process has two separately authorized BusinessTaskPackages, two agent builds and one shared test interaction. Agents can fail due to prompt, tools/MCP, ReAct workflow, memory/recovery, RAG, model choice or protocol compatibility. The factory needs distinct per-tenant optimization and model cost/quality experiments, then independent AgentStore version publication.

## Scope
- Two independent, permission-scoped Builder jobs started explicitly by Orchestrator using the same scalable Builder service.
- Durable and memory-aware harness present from version 1; optimize allowed surfaces only.
- Cross-company quality attribution with A/B and joint acceptance, error classification, GEPARD and optional Soup.
- A versioned AgentStore with independent release and rollback for each organization.
- A separate, measured model replacement benchmark through LiteLLM and Evaluation; cheaper models may be promoted only when no unacceptable regression is established with sufficient evidence.
- Cross-play with frozen counterpart versions to prevent co-adaptation.

## Dependencies and governance
Builds upon bootstrap-factory-mvp and a2a-bilateral-evaluation. Exact microservice topology and AgentStore deployment require owner-approved ADR-0002. No runtime or production feature is implemented by this change. See docs/architecture/TWIN_AGENT_HARNESS_RFC.md.

## Non-goals
Training on another firm's private data, accessing hidden reasoning or evaluation holdouts, mutating production prompt/models directly from GEPARD, installing unapproved MCP, promising cheaper LLM quality without comparative tests, or treating a checkpoint as exactly-once external business effects.
