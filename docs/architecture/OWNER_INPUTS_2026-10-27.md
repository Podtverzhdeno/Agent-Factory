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

Latest owner follow-up: explicitly selected option A (Python-native LangGraph/PostgreSQL runtime). LiteLLM was questioned; it is NOT an approved MVP gateway and should remain optional, behind a ModelGateway contract. An extra proxy is justified only by actual multi-provider routing, centralized budgets/keys or governance needs.

Remaining open decisions: (a) exact deployable service boundaries; (b) REST/Kafka final topology; (c) deployment/hosting plan; (d) physical vs logical service databases; (e) agent container scale and security.