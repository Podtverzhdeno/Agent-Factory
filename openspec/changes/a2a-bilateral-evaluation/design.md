# Design — Bilateral A2A Evaluation (DRAFT)

See docs/architecture/A2A_BILATERAL_EVALUATION_RFC.md for business rationale, data boundaries, proposed API and complete conversation optimization loop.

## Candidate responsibilities

Orchestrator (Java Spring Boot) owns scenario lifecycle and optimization/release decisions. Evaluation (Python) owns independently versioned A2A simulator workers, full outcome evaluation and hidden gold. Generated Python/LangGraph Agent Runtime A and B run in isolated containers with official A2A interfaces. GEPARD optimizes an expressly authorized agent using its own config and allowed sanitized A2A trace slices; Soup remains optional, invoked by Orchestrator rather than GEPARD. Tool/MCP Registry is centralized, LiteLLM mediates inference and service DBs remain separately owned.

## Sequence

Orchestrator: validate bilateral consent + pinned A0/B0/scenario version → issue explicit REST evaluation command.
Evaluation: provision isolated agents, invoke real A2A transport, record consent-scoped task/message/artifact events → independently assess outcome_A, outcome_B and joint_outcome, disclose only permitted findings → emit completed/blocked event via Kafka.
Orchestrator: diagnose and choose target A or B; obtain tenant authorization → invoke GEPARD with tenant-scoped candidate inputs.
Evaluation: cross-play updated A1 against B0, A0 against B1, and authorized A1 against B1, plus held-out counterpart variants.
Orchestrator: apply per-tenant quality gates; issue independent release commands with separate approvals; rollback regression.

## Model contracts

BilateralScenario version, BilateralRun ID, AgentSpec hashes, A/B tenant principals, granted public dialog artifacts, A2A protocol version and capabilities, private evaluation oracles, policy and budget versions, trace provenance. Cross-company transcript must not be used as a shared training set without informed permission from each party.

## Tests

Protocol conformance: discover capabilities, auth, text/structured/file Parts, Task progress and terminal states, streaming/disconnection as supported by both endpoints.
Business evaluation: correct resulting artifact and authorized external effects, not just fluent messages.
Robustness: missing document, ambiguous request, changed field/unit, timeout/cancellation, incomplete answer, version incompatibility, prompt injection, cross-tenant access denial, negative disclosure.
Optimization: compare baseline A0/B0 to independent A1/B0, A0/B1 and A1/B1 plus held-out third-party/frozen counterpart. Safety gates independent for A and B; never promote on joint score alone.

## Alternatives

- Deploy new stand-alone A2A Evaluation Service vs simulation workers inside existing Evaluation: choose after load and isolation profiling. No new service mandated by this proposal.
- Joint optimizer shared across both tenants vs Orchestrator-controlled per-tenant GEPARD campaigns: proposed per-tenant because shared optimization can leak proprietary knowledge or optimize against one firm's benefit.
- Raw transcript training vs sanitized consent-scoped evidence: reject raw cross-tenant training by default.

## Pending decisions

Owner agreement on milestone, information sharing, consent, bilateral version release and deployable boundary.
