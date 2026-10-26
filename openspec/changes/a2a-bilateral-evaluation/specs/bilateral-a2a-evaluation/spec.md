## ADDED Requirements

### Requirement: AF-REQ-031 — Independently authorized bilateral scenarios
The factory SHALL represent an A2A interaction between two independent organizations as a versioned scenario with pinned agent/task versions and explicit per-tenant permissions.

#### Scenario: Authorized buyer-supplier case
- **WHEN** both organizations approve a scenario and their independent agent/policy versions
- **THEN** the Orchestrator can request a sandbox bilateral A2A simulation without merging their private credentials or datasets

#### Scenario: Unauthorized cross-company optimization
- **WHEN** one organization requests changes to the other's agent without that organization's authorization
- **THEN** the system denies the change and records the security event

### Requirement: AF-REQ-032 — Protocol-faithful multi-turn A2A simulation
The factory SHALL execute both agents through their published A2A interface using stateful Tasks, Messages, Parts and business Artifacts while recording a consent-limited, reproducible test trace.

#### Scenario: Clarification and file exchange
- **WHEN** the buyer sends an incomplete RFQ with a document and the supplier requests clarification
- **THEN** the simulator executes the permitted dialogue, records valid task transitions and checks returned Artifact structure and references

#### Scenario: Interrupted partner
- **WHEN** one A2A party times out or disconnects during an asynchronous task
- **THEN** the simulation records the fault, validates recovery/terminal outcome and does not duplicate consequential tool effects

### Requirement: AF-REQ-033 — Independent and joint business quality
The factory SHALL evaluate party A's business outcome, party B's business outcome and shared end-to-end result separately, with each party's critical policy constraints as non-negotiable release gates.

#### Scenario: Joint success violates one party's policy
- **WHEN** dialogue completion improves but one participant disclosed prohibited business information
- **THEN** the joint quality score cannot override the violating participant's safety failure and no unsafe candidate is released

### Requirement: AF-REQ-034 — Tenant-scoped interaction optimization
The factory SHALL permit Orchestrator-directed GEPARD optimization of one or both agents based only on approved dialogue excerpts and that organization's accessible AgentSpec, without granting access to the other organization's internal prompts or sealed gold answers.

#### Scenario: Agent A improves response format
- **WHEN** a trace shows agent A used an invalid data structure and its owner approved optimizing A
- **THEN** GEPARD can produce a new immutable candidate A1 for sandbox testing without mutating agent B or production A0

### Requirement: AF-REQ-035 — Cross-play independent regression
The factory SHALL validate changes against frozen and held-out counterpart configurations in addition to jointly optimized agent pairs.

#### Scenario: Co-adapted agents only work with one another
- **WHEN** candidate agents A1 and B1 succeed together but A1 fails against the approved frozen baseline B0
- **THEN** the candidate cannot be promoted on joint score alone and the regression is reported

### Requirement: AF-REQ-036 — Bilateral consent and trace isolation
The factory SHALL enforce explicit legal/data-use permissions, tenant isolation, trace redaction and retention for cross-organizational dialogue evaluation, optimization and model training.

#### Scenario: Confidential supplier data in dialogue
- **WHEN** an A2A artifact contains supplier-confidential content not approved for the buyer or shared optimization
- **THEN** that information is withheld/redacted from the buyer's datasets and GEPARD training view

### Requirement: AF-REQ-037 — Verify business outcome beyond conversation state
The factory SHALL verify business Artifacts and authorized business effects independently of A2A conversational fluency or terminal task status.

#### Scenario: Fluent dialogue without correct proposal
- **WHEN** two agents complete a protocol task but no valid matching quotation artifact is produced
- **THEN** the scenario is marked FAILED rather than treating A2A task completion as business success
