# Owner architecture inputs — captured from discussion

Provenance: direct owner responses in chat on the project architecture; these requirements are owner-stated but NOT an approved topology in GitHub.
Owner: @Podtverzhdeno. Architecture style: MICROSERVICES. Ratification: PENDING.

1. Desired pipeline: create agent -> add harness and Pi Durable -> test on real business tasks -> optimize gaps via separate GEPARD and optional standalone Soup -> retest -> expose via A2A.
2. Agents: a separate container per agent is preferred, but owner explicitly asks whether a shared execution service is more efficient.
3. Factory/build plane and agent execution should be separated; hosting on client infrastructure is NOT planned for now.
4. REST and Kafka are candidates, and owner requests advice, not an automatic final decision.
5. Distinct database ownership per service is required; physical Postgres-instance count is not decided.
6. Python for agent code, Java Spring Boot for reliable backend/control services; Langfuse for traces; other components requested as recommendations.
7. GEPARD is a separate service; the factory must provide durable execution to generated agents. **Latest owner decision:** choose Python-native Agent Runtime with LangGraph + PostgreSQL checkpointing for MVP; Pi Durable stays as a separate research PoC, not a mandatory implementation dependency. Soup is a standalone optional service.
8. One central Tool/MCP Registry is required and the factory selects the needed tools automatically.
9. Infrastructure answer: 'all together'; specific Compose/Kubernetes/hosting decision requires interpretation/confirmation.
10. Architecture should support horizontal scaling from day one.

IMPORTANT: The owner still needs to personally accept or change the recommended service map in ADR-0002. No AI-generated ADR is owner-approved.

Latest owner follow-up: explicitly selected option A (Python-native LangGraph/PostgreSQL runtime). LiteLLM was initially questioned. **LATEST OWNER DECISION: ADD LiteLLM to MVP architecture** as shared, centralized LLM Gateway. Route Agent Runtime and GEPARD inference through it; centralize provider credentials, per-agent/tenant limits, usage auditing and model routing. Physical service placement/configuration remains subject to owner approval of full ADR-0002.

Remaining open decisions: (a) exact deployable service boundaries; (b) REST/Kafka final topology; (c) deployment/hosting plan; (d) physical vs logical service databases; (e) agent container scale and security.

## Owner review of C4 Level 2 (2026-10-27)

The owner explicitly corrected three interactions:
1. Factory Orchestrator directly invokes Agent Builder to create agents. Kafka is a transport for deliberately published messages and events; it does not independently decide to build.
2. GEPARD is directly connected to the agent: it obtains the actual system prompt/harness/configuration, tests changes and should automatically apply demonstrated improvements.
3. Soup is invoked directly by Factory Orchestrator, NOT by GEPARD. The orchestrator can initiate specialized fine-tuning based on evidence of a model limitation or an explicit request to specialize.

**Implementation safety interpretation (assistant proposal awaiting topology ratification):** Read production AgentSpec/config through an authorized versioned agent API and/or artifact repository. Write candidate revisions into isolated evaluation runtime; only Orchestrator promotes a candidate after independent evaluation, safety checks and any mandatory approval. Default safe automatic promotion for low-risk changes is allowed by policy; no unsafe direct mutable production edit.

## Product priority clarified by owner — 2026-10-27

**PRIMARY: one specialized B2B agent** built and independently evaluated for one organization's Business Task Package. A2A endpoint support remains useful for future interoperable invocation. **OPTIONAL: bilateral A2A agent building/optimization between two firms**; this must not be a mandatory MVP condition, require two paying customers or become the main commercial sales funnel. Global competitors already cover many GEPARD-like improvement, evaluation, model routing and durable functions, so competitive uniqueness is not assumed.
