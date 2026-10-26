# Architectural workshop — owner decisions

Architecture owner: @Podtverzhdeno.
Confirmed: MICROSERVICES.
Status: OWNER INPUT PENDING.

This document is a questionnaire, NOT an approved solution. The assistant can give alternatives and feedback; it cannot fill Owner decision fields or approve on behalf of the project owner.

## Q1 — MVP scope and deployment unit
Which two business tasks are in the first pilot? Does each generated agent require its own deployable service, or can different agents share a tenant-isolated runtime pool?
Owner decision: TBD

## Q2 — Service boundaries
Which independently deployed services should exist at MVP? Consider the following ONLY as candidate responsibilities: factory control plane; tools/MCP registry; agent runtime; evaluation and optimization; integration/A2A gateway. Which should be combined/split, and why?
Owner decision: TBD

## Q3 — Control plane vs data plane
Should factory/build-time infrastructure be separate from live client agent execution? Is on-prem client runtime a near-term requirement?
Owner decision: TBD

## Q4 — Service communication
What is used for synchronous calls (REST/gRPC) and for async jobs/events (Kafka/RabbitMQ/NATS/other)? Which use cases require messaging guarantees?
Owner decision: TBD

## Q5 — Data ownership
Which service owns each database/schema? Which data require PostgreSQL, cache, object storage, event log, vector store or secret vault? How do services coordinate without editing each other's tables?
Owner decision: TBD

## Q6 — Languages and durable runtime
Python only, TypeScript only, or polyglot? Is Pi Durable required for the pilot, or an experiment evaluated against LangGraph/Temporal?
Owner decision: TBD

## Q7 — Optimization and training
Is GEPARD a dedicated microservice or a job worker inside another service? Is Soup/LoRA a separate offline training worker? Which component approves new prompt/model versions?
Owner decision: TBD

## Q8 — Trusted tools and MCP
Where are trust policies, secrets, scopes and sandbox boundaries enforced? Can users manually register an untrusted MCP, and what approval is required?
Owner decision: TBD

## Q9 — A2A exposure
Separate A2A endpoint for each customer agent or a shared gateway with routing? What identity and authorization model?
Owner decision: TBD

## Q10 — Infrastructure
Where do MVP services run: Docker Compose, Railway, managed containers, Kubernetes, customer on-prem? Budget and expected operations capacity?
Owner decision: TBD

## Q11 — Isolation and observability
Single/multi-tenant? What are acceptable latency, uptime, trace retention and recovery expectations?
Owner decision: TBD

## Q12 — Trade-offs
What dominates the pilot: simplicity, independent scalability, resilience, low cost, security, development speed? How many developers/operators support it?
Owner decision: TBD

## Ratification process
1. Owner personally answers the questions and modifies the service architecture ADR.
2. Assistant reviews risks, alternative boundaries and interaction contracts; proposals stay DRAFT.
3. Owner personally approves the ADR through a traceable GitHub action; link actual commit/review in ADR.
4. Only after owner approval may service topology be implemented. AI-created approval text cannot replace an actual owner action.
