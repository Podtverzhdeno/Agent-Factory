## ADDED Requirements

### Requirement: AF-REQ-041 — Grounded tool, MCP and prompt improvement
The factory SHALL allow bounded prompt and supported model-facing tool/argument description optimization with actual trace feedback, registry compatibility checks and independent post-change evaluation, without mutating tool implementation or authority.

#### Scenario: Wrong catalog tool
- **WHEN** an agent selects the wrong tool due to an ambiguous description
- **THEN** the optimizer may propose an improved description, but must verify unchanged tool schema, allowed scopes and task quality before a new AgentSpec version is eligible

### Requirement: AF-REQ-042 — Observable ReAct and graph testing
The evaluator SHALL inspect observable tool calls, parameters, actions, graph transitions, retry/stop behavior and verified results for agentic workflows, without depending on inaccessible hidden model reasoning.

#### Scenario: False completion
- **WHEN** an agent claims an external action completed without the required authorized tool effect
- **THEN** the task fails and its missing action is linked to traceable graph/tool evidence

### Requirement: AF-REQ-043 — Short and long-term memory quality
The factory SHALL evaluate thread-scoped short-term continuity/checkpoints separately from tenant-scoped long-term store retrieval, write, TTL, deletion, provenance and privacy controls.

#### Scenario: Expired supplier fact
- **WHEN** agent A retrieves an expired fact from long-term memory
- **THEN** the fact is not treated as authoritative and the evaluator records a freshness violation

#### Scenario: Private memory across organizations
- **WHEN** agent B attempts to read agent A's private long-term memory
- **THEN** the store rejects access and logs a tenant-bound security incident

### Requirement: AF-REQ-044 — Failure attribution and independent cross-play
The factory SHALL score each organization's task success and privacy policy independently from joint A2A completion, attribute failures to responsible agent surfaces, and reject candidates that overfit to a jointly optimized partner alone.

#### Scenario: Buyer schema failure
- **WHEN** B supplies a correct A2A Artifact but A misinterprets its measurement units
- **THEN** Evaluation attributes the defect to A and tests A's candidate against frozen B and unseen partner cases
