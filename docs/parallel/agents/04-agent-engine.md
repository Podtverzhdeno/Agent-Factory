# AGENT 04 — Agent Builder, Python Runtime and LiteLLM Adapter

**Branch:** agent/04-agent-engine
**You own only:** \`services/agent-builder/**\`, \`services/agent-runtime/**\`, \`services/litellm-adapter/**\`, \`tests/agent-engine/**\`
**Stack:** Python 3.12+, Pydantic, LangGraph, PostgreSQL checkpoint adapter, A2A SDK adapter, typed LiteLLM client port. Builder and Runtime are two proposed deployables, one developer work packet.
**Relevant requirements:** AF-REQ-005/006/007/012/013/016/023/029, AF-REQ-039/040/042/043. Full bilateral A2A optimization is optional after MVP.

## One independently owned task

From a mocked READY Task Snapshot and mocked eligible Tool/MCP Registry, generate an immutable **minimum sufficient AgentSpec**; run it in a safe, tenant-isolated Python/LangGraph candidate Runtime with ReAct-style observable tool execution, typed I/O, basic scoped memories, resumable checkpoints, and approved A2A interface. LiteLLM access is via an adapter and fake endpoint for tests. Do NOT own central release or evaluation judgments.

## Components

- **Builder**: analyze approved rules/files and required capabilities, deterministic eligibility/minimal coverage, generate initial prompt + graph + tool grants + model route + memory/retry configuration as versioned AgentSpec, fail BLOCKED on missing tools/authority.
- **Runtime**: load only pinned AgentSpec versions, run signed allowed tool calls with typed args, bounds, timeout, idempotency and protected state; keep short-term thread/checkpoint state separate from tenant-scoped long-term memory. Include official A2A transport adapter, not a custom business protocol.
- **Model port**: LiteLLM-compatible provider abstraction for token/cost and model IDs; no direct provider secrets in AgentSpec. Configure mock route and model-denied/budget exhausted cases without shipping a full production LiteLLM cluster.
- **Observability**: trace IDs and deterministic observable graph/tool events. Do not claim access to hidden chain-of-thought.

## Deliverables

1. Typed AgentSpec, BuildJob port/handler, deterministic capability-to-tool coverage with failure reasons.
2. Controlled baseline harness and graph execution with minimal tools: read source XLSX, authorized fake catalog lookup, render a draft output artifact via fake storage ports.
3. LangGraph/Postgres checkpointer behind a port, crash/restart/idempotent-effect scenario; test both read-only success and prohibited write rejection.
4. Memory tests for per-thread continuity, long-term scoped retrieval, stale or cross-tenant memory denial.
5. A2A conformance client/server smoke (using approved SDK) with auth and explicit denial.
6. LiteLLM mock tests for allowed route, unavailable provider, exhausted budget and source attribution; actual shared proxy infrastructure managed by integration owner later.
7. Runnable isolated demo + tests + PR with exact evidence.

## Acceptance

Two distinct synthetic BTP snapshots produce different immutable AgentSpecs from the same Builder source; both can execute against mocked tools in separate Runtime instances. A kill/retry does not double-apply an external effect. A2A request conforms and rejects unauthorized callers. Tests require no agent 01/02/03/05 live services.

## Exclusions

Do not parse documents (02), approve tools (03), compute business PASS (05), auto-release (01), run Soup training or refactor shared specs. If an official SDK version creates friction, document real limitation and test mock contracts rather than inventing compliance.

## Copy/paste launch prompt

> Own workstream **04 Agent Engine** on branch **agent/04-agent-engine**. First read \`AGENTS.md\`, \`docs/parallel/README.md\`, \`docs/parallel/CONTRACTS_V0.md\`, \`docs/architecture/TWIN_AGENT_HARNESS_RFC.md\` and this task file. Work only in \`services/agent-builder/**\`, \`services/agent-runtime/**\`, \`services/litellm-adapter/**\`, \`tests/agent-engine/**\`. Using mock BTP/Tool Registry, build versioned AgentSpec and Python LangGraph runtime with persistence, scoped memory, tool policy and A2A adapter; execute negative tests and open PR into \`docs/sdd-foundation-mvp\`. Do not edit sibling services/shared specs or bypass ADR-0002. Report verified versus blocked features accurately.
