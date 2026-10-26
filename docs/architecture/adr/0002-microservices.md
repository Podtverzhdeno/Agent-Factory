# ADR-0002 — Owner-defined microservice architecture

Status: PENDING OWNER DECISION
Style: MICROSERVICES (selected by owner)
Decision owner: @Podtverzhdeno
Owner authorship / approval evidence URL: PENDING
Date ratified: PENDING

## Context
The factory assembles minimal B2B agents, verifies their outcomes, applies bounded GEPARD/harness optimization, and offers portable durable execution and optional model fine-tuning.

## Decisions to be written personally by the owner
1. MVP deployable services and bounded contexts: TBD
2. Responsibilities, service owners and API boundaries: TBD
3. Control-plane/data-plane separation: TBD
4. Sync and async communication: TBD
5. Database/data ownership and consistency: TBD
6. Language/runtime strategy: **Python Agent Runtime with LangGraph/PostgreSQL checkpoints selected by owner in chat for MVP**; Pi Durable stays an optional separate PoC. Overall service topology approval still pending.
7. GEPARD and Soup deployment boundaries: TBD
8. MCP trust boundary and secrets policy: TBD
9. A2A gateway and tenant authorization: TBD
10. Hosting/deployment, observability, SLO: TBD
11. LLM routing: owner chose **LiteLLM Gateway** for MVP. Agent Runtime and GEPARD route inference through it; specific service topology, budgets, credential ownership and deployment are still to be approved in GitHub.

## Decision log (not ADR ratification)

- Owner confirmed in chat: **variant A**, Python-native LangGraph/PostgreSQL runtime.
- Owner's latest decision: **include LiteLLM as the centralized LLM Gateway from MVP**, with provider key isolation, quotas, usage tracking and a separate service-owned database.
- Formal ratification of the full ADR must still come from the owner's own traceable GitHub review/commit.

## Additional explicit owner feedback: C4 Level 2 links

- Orchestrator MUST directly initiate Builder, not merely publish an ambiguous Kafka event.
- GEPARD MUST interact with a particular agent configuration including the system prompt and harness, and its accepted improvements should automatically reach the running agent after quality-controlled release.
- Soup MUST be initiated independently by the Orchestrator, never implicitly by GEPARD. The Orchestrator may decide from diagnostic evidence or explicit user desire to specialize.
- Proposed safe interpretation: authorized read from agent/versioned artifacts; candidate optimization in sandbox; independent evaluation; Orchestrator-controlled automatic low-risk promotion, approvals for sensitive side effects.

Specific endpoints and the complete topology remain PENDING owner ratification.

## Required architectural evidence
Owner-authored C4 container diagram, communication/data ownership map, representative request/async sequence, failure and security model, alternatives considered and rationale. Refer to ../OWNER_QUESTIONNAIRE.md.

## Guard
An assistant SHALL NOT mark this ADR ACCEPTED, infer the owner's decisions or implement service boundaries while owner sign-off is missing. Review/commit links from real GitHub actions are mandatory.
