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
6. Language/runtime strategy; Pi Durable placement: TBD
7. GEPARD and Soup deployment boundaries: TBD
8. MCP trust boundary and secrets policy: TBD
9. A2A gateway and tenant authorization: TBD
10. Hosting/deployment, observability, SLO: TBD

## Required architectural evidence
Owner-authored C4 container diagram, communication/data ownership map, representative request/async sequence, failure and security model, alternatives considered and rationale. Refer to ../OWNER_QUESTIONNAIRE.md.

## Guard
An assistant SHALL NOT mark this ADR ACCEPTED, infer the owner's decisions or implement service boundaries while owner sign-off is missing. Review/commit links from real GitHub actions are mandatory.
