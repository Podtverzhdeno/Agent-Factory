# RFC — Bilateral A2A Simulation, Evaluation and Optimization

**Status:** assistant proposal, owner architecture review required; NOT deployed, NOT owner-ratified.
**Product hypothesis:** the factory should verify and improve *business outcomes across independent organizations*, not just individual LLM agent scores.

## Motivation and protocol grounding

A2A is a transport/interaction protocol. Its Task, Message, Part, Artifact, AgentCard, task lifecycle and asynchronous operations support interoperable business communication, but protocol compliance alone does not measure correct business outcomes. Official specification: https://a2a-protocol.org/v1.0.0/specification

Research warning: multi-turn inter-agent scenarios introduce contextual safety/privacy vulnerabilities. ConVerse (EACL Findings 2026) covers contextual privacy/security risks in agent-to-agent conversations: https://aclanthology.org/2026.findings-eacl.170/

## Scenario: two organizations

- **Organization A:** buyer. Private ERP/catalog access, procurement rules, permitted disclosures, approved budget and human approval rules.
- **Organization B:** supplier. Own inventory/catalog, commercial policy, response format, permissions, approved disclosures and approvals.
- **Joint business outcome:** create a compliant, correctly matched quotation/proposal with evidence; confirm receipt and exceptions. No live payment, signature, purchase order or customer outreach in sandbox.
- **Crucial separation:** the buyer and supplier have independent principals, secrets, policies, prompts, source files, evaluation metrics, approval authorities and release artifacts.

Agents communicate **only** over the selected official A2A binding, using the public interface. One does not read the other's private prompts, chain of thought, credentials, data store or hidden evaluation answers.

## Proposed architecture — do not infer new microservices without owner decision

~~~mermaid
flowchart TB
    OA["Company A: buyer BusinessTask / dataset"] --> OR["Factory Orchestrator (Java)"]
    OB["Company B: supplier BusinessTask / dataset"] --> OR
    OR -->|"Provision candidate A"| A["Agent Runtime A (Python / LangGraph)"]
    OR -->|"Provision candidate B"| B["Agent Runtime B (Python / LangGraph)"]
    OR -->|"Explicit REST: run cross-org scenario"| SIM["A2A Simulation Harness (Evaluation workers)"]
    SIM -->|"A2A Task/Message/Artifact"| A
    SIM -->|"A2A Task/Message/Artifact"| B
    A <-->|"A2A communication under bilateral scopes"| B
    SIM -->|"Tenant A private score"| EA[("Evaluation private A")]
    SIM -->|"Tenant B private score"| EB[("Evaluation private B")]
    SIM -->|"Joint public-safe result"| JO[("Aggregate report")]
    OR -->|"Target A optimization if authorized"| GA["GEPARD candidate A"]
    OR -->|"Target B optimization if authorized"| GB["GEPARD candidate B"]
    GA -->|"Authorized tenant A config only"| A
    GB -->|"Authorized tenant B config only"| B
    OR -->|"Release separately per tenant"| REL["Independent versioned release gates A & B"]
~~~

- The **Orchestrator** explicitly starts tests and invokes optimization; Kafka publishes lifecycle events only after handlers perform requested work.
- The **Evaluation Service** owns simulated counterparty interactions and independent outcome oracles. A simulation worker is a logical component, not necessarily a separate deployable microservice.
- **GEPARD** can optimize a particular agent using that organization's authorized prompt/harness traces, public/shared dialogue transcript and sanitized diagnostics. It may not read the other tenant's confidential config or sealed labels.
- Soup remains directly invoked by the Orchestrator under organization-specific consent; never automatically trains on the counterparty's data.
- **Deployment Controller** separate vs Builder responsibility remains an owner decision. The simulation uses isolated containers and mock/sandbox tools only.

## Lifecycle

1. Each organization independently creates/approves its BusinessTaskPackage (BTP), scopes and expected outcomes.
2. Orchestrator builds agent A and B independently. Each agent passes its own basic unit, protocol, privilege and task tests first.
3. An authorized bilateral scenario is configured: counterpart pair, versions, initial buyer request, allowed artifacts, business invariants, per-side visibility, protocol capabilities and budget.
4. Orchestrator starts sandbox A2A run. A and B interact via published AgentCards and authenticated A2A Task/Message/Part/Artifact flow. Record protocol traces under consent and retention policy; do not assume A2A Task history contains every message — harness controls its own auditable capture.
5. Evaluation checks **three** outputs independently:
   - A's individual utility, policy compliance and resource consumption.
   - B's individual utility, policy compliance and resource consumption.
   - Verifiable joint business result and interoperable protocol behavior.
6. Diagnose root cause: incomplete requirements, tool gap, data mismatch, misunderstanding, unnecessary turns, wrong data format, protocol error, missing authorization, transient failure.
7. Orchestrator initiates bounded GEPARD optimization for A or B separately (or authorized paired experiment), creating immutable candidate versions.
8. Evaluate candidates in a **cross-play matrix** to avoid fragile co-adaptation:
   - A1 vs B0
   - A0 vs B1
   - A1 vs B1
   - A1 against a separately frozen/alternative counterparty profile if available
   Regression in either organization's independent constraints blocks that party's promotion.
9. Independent holdout, privacy, disclosure and approval gates. Orchestrator releases A and B **separately**, not as one inseparable bundle; both approvals are required for coordinated rollout if it changes their shared protocol contract.
10. Post-release shadow/canary dialogues (with consent), alerts and rollback. Never automatically train from raw sensitive production conversations.

## Objective design

Avoid optimizing only number of messages, token cost or total business utility: it can create unsafe disclosures, hidden coordination or disadvantage one company. Use constrained multi-objective optimization:
- HARD: authorization, non-disclosure, contractual rules, correct counterpart authentication, prohibition of hidden cross-tenant data access and unsafe tool effects.
- A: its independently defined task completion / accuracy / approval obligations / cost.
- B: its independently defined completion / inventory correctness / contractual policy / cost.
- Joint: verified end-to-end task completion, time-to-completion, number of productive turns, protocol errors, file/artifact correctness, recovery and handoffs.
- Decision: no candidate is promoted if A or B violates their hard constraints, even if joint score improves. Compare candidate against tenant baseline and held-out counterpart variants; report Pareto trade-offs rather than imposing shared weights without consent.

## Data and consent

Bilateral tests need both parties' consent or approved synthetic fixtures. The factory must enforce:
- Separate tenant keys, storage, prompts, datasets, source files and role grants.
- Shared information limited to exchanged A2A Messages/Artifacts and explicitly permitted public/sanitized parts of the transcript. Private internal traces belong to their origin tenant.
- No direct exposure of one tenant's evaluation gold, proprietary negotiation limits, ERP prices/cost or business policies to other tenant or its GEPARD instance.
- Cryptographically/auditably distinct run IDs, agent version IDs, context/task IDs, test dataset versions, policy version, consent and trace visibility.
- Data minimization, retention and deletion policies; no turning private transcripts into a shared fine-tuning corpus without separate permissions.
- No unilateral orchestrator override of either organization's protected constraints.

## Suggested type contracts

**BilateralScenario**:
- scenario_id, revision, owner_of_scenario, organization_A_id, organization_B_id
- agent_A_spec_hash, agent_B_spec_hash, A2A protocol version & capabilities
- permitted public business intent, approved scenario fixtures and attachment hashes
- read/write scopes, allowed information sharing, authorized test identities
- private_A_oracle_ref, private_B_oracle_ref, joint_oracle_ref (references not leaked through counterpart)
- attempt/token/cost/time/turn budgets; timeout/retry/cancellation rules

**BilateralRun**:
- run_id, scenario_revision, both agent version hashes, shared A2A task/context IDs
- event timestamps, message/part/artifact references with disclosure classification
- tool-effect proofs, protocol conformance, individual A/B metrics, joint metrics
- cause taxonomy, candidate A/B versions, release/approval state and trace pointers

API draft (awaiting owner approval):
- POST /v1/a2a-evaluations — Orchestrator issues explicit evaluation of two candidate version IDs + scenario revision; returns 202/run_id
- GET /v1/a2a-evaluations/{run_id} — returns caller-authorized aggregate plus own organization details
- POST /v1/a2a-evaluations/{run_id}/optimize — Orchestrator authorizes per-tenant target agent and budget after diagnosable results
- Kafka events: a2a.evaluation.started / completed / blocked and candidate.evaluated; only IDs, sanitized metadata and versions, NEVER binary documents or raw private dialogue

## MVP / pilot phase

**P1 experiment**, not blocker for initial single-agent factory:
1. Create two synthetic organization BTPs: buyer and supplier.
2. Generate two different AgentSpecs from the same factory using only approved MCP/API sandbox fixtures.
3. Execute at least 20 varied synthetic dialogues, including valid RFQ, missing SKU, ambiguous grade/CAS, missing docs, invalid price/quantity units, schema mismatch, slow counterparty, one offline agent, malicious instruction in artifact, disallowed disclosure.
4. Compare immutable baseline A0+B0 against one candidate update at a time and joint A1+B1. Do not claim 20 examples establish statistical generality; larger gold and hidden holdout are required for release.
5. Report per-side and joint metrics, trace evidence, costs, changed AgentSpec hashes and rollback.
6. Check both parties' goals and invariants; freeze unseen counterparty cases for acceptance.

**Go/No-go research question:** Do independent Agent Factories improve *cross-company business completion and operating cost* over fixed baseline agents without illicit sharing of private information, overfitting to each other or requiring bespoke coding for each partner?

## Open owner decisions

- Is multi-organization optimization a first MVP acceptance scenario or a separate P1 milestone?
- May one organization request optimization of the other organization's agent, or must each separately authorize it? Strong recommendation: independent authorization.
- Which portions of A2A dialogue can both parties see/store for optimization?
- Are jointly proposed protocol schema changes allowed only after both parties approve a new contract version?
- Who owns the simulator and the shared sanitized benchmark, and who signs off the independent gold truths?
