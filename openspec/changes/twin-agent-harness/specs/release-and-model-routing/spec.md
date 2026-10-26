## ADDED Requirements

### Requirement: AF-REQ-045 — Tenant-owned AgentStore versions
The factory SHALL publish only approved, immutable versions of tenant-owned agents to AgentStore, recording AgentSpec hashes, runtime/model/tool versions, approved A2A Agent Cards, independent business test evidence, compatibility and rollback metadata.

#### Scenario: Successful bilateral acceptance
- **WHEN** independent A/B gates and shared A2A contract tests pass with each owner's release authority
- **THEN** AgentStore publishes separately approved Agent A and B versions with auditable evidence and rollback targets

#### Scenario: Only one side approves
- **WHEN** A authorizes its release but B withholds authorization
- **THEN** B's candidate version is not published or changed by A's decision

### Requirement: AF-REQ-046 — Orchestrator-owned optimization decisions
Orchestrator SHALL select bounded GEPARD configuration campaigns, trusted deterministic harness corrections or separately authorized Soup model training based on diagnosable evidence and budgets, always followed by independent re-evaluation.

#### Scenario: Model limitation after harness repairs
- **WHEN** repeated failures indicate a model limitation and eligible private training samples exist
- **THEN** Orchestrator may initiate Soup directly without requiring GEPARD to call it, but cannot release the model without new acceptance tests

### Requirement: AF-REQ-047 — End-to-end paired-agent factory proof
The pilot SHALL prove two separately owned task packages become two independently configured agents that complete a real protocol-level simulated A2A business workflow, permit targeted repairs and receive versioned release only after independent acceptance.

#### Scenario: Repair one side
- **WHEN** agent A's approved prompt causes a resolvable A2A failure and B is already correct
- **THEN** the factory proposes A1, independently tests A1 against B0 and held-out cases, and does not unnecessarily alter B

### Requirement: AF-REQ-048 — Quality-preserving model cost optimization
The factory SHALL independently benchmark eligible lower-cost models or routing policies per agent and graph step through LiteLLM, and promote a replacement only after versioned held-out evidence demonstrates required business quality non-inferiority, both organizations' hard constraints, expected end-to-end savings and safe rollback.

#### Scenario: Cheaper model preserves completion and policy
- **WHEN** a candidate model meets required features, passes independent held-out A2A cross-play, satisfies an owner-defined non-inferiority margin and lowers attributable cost per correct business operation
- **THEN** Orchestrator may approve a new pinned AgentSpec model route under the tenant's release policy without altering the other organization's version

#### Scenario: Cheapest model loses tool correctness
- **WHEN** a cheaper candidate omits mandatory tool calls, misuses MCP or violates one party's safety constraints
- **THEN** the candidate fails regardless of token price and baseline remains active

#### Scenario: Insufficient statistical evidence
- **WHEN** the benchmark lacks enough independent unseen cases to establish non-inferiority
- **THEN** the candidate remains INCONCLUSIVE and cannot be claimed quality-equivalent or automatically released

#### Scenario: Model capability mismatch
- **WHEN** a proposed cheaper model lacks required tool-calling, JSON schema, context length or approved processing region
- **THEN** the benchmark rejects it before promotion and explains the failed eligibility check
