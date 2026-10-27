## ADDED Requirements

### Requirement: AF-REQ-001 — Formal task intake
The factory SHALL accept a versioned BusinessTask describing the B2B objective, tenant, typed inputs/outputs, allowed effects, dependencies, budgets and acceptance criteria rather than interpreting a vague prompt as sufficient authorization.

#### Scenario: Valid constrained task
- **WHEN** a task includes required contracts, measurable criteria and explicit allowed operations
- **THEN** the factory persists the task version and returns a unique task identifier

#### Scenario: Missing testable outcome
- **WHEN** the requester omits measurable acceptance criteria
- **THEN** the factory returns BLOCKED with missing information and does not claim an agent can be verified

### Requirement: AF-REQ-002 — Gap-aware task analysis
The factory SHALL distinguish available capabilities from unavailable data, permissions and integrations before an assembly attempt.

#### Scenario: Missing production API credentials
- **WHEN** a task requires a protected ERP endpoint without approved credentials
- **THEN** the factory requests an authorized connector grant and does not create fake production access
