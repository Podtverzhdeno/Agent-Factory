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

## Decision log (not ADR ratification)\n\n- Owner confirmed in chat: **variant A**, Python-native LangGraph/PostgreSQL runtime.\n- LiteLLM is not mandated; it remains optional unless multiple providers, routing, or central budget/credential controls justify a separate gateway.\n- Formal ratification of the full ADR must still come from the owner's own traceable GitHub review/commit.\n\n## Required architectural evidence
Owner-authored C4 container diagram, communication/data ownership map, representative request/async sequence, failure and security model, alternatives considered and rationale. Refer to ../OWNER_QUESTIONNAIRE.md.

## Guard
An assistant SHALL NOT mark this ADR ACCEPTED, infer the owner's decisions or implement service boundaries while owner sign-off is missing. Review/commit links from real GitHub actions are mandatory.
