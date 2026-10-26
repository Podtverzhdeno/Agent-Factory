## ADDED Requirements

### Requirement: AF-REQ-012 — Recoverable long-running tasks
The factory SHALL checkpoint resumable tasks through a replaceable durable runtime while preventing duplicate consequential actions.

#### Scenario: Crash after external operation
- **WHEN** a worker crashes after an authorized order mutation but before acknowledging completion
- **THEN** resume reconciles the external effect using an idempotency key instead of submitting the mutation again

### Requirement: AF-REQ-013 — Interoperable A2A interface
A released agent SHALL expose an authorized A2A-compatible invocation boundary independent of its implementation framework.

#### Scenario: Independent client invocation
- **WHEN** a separately deployed authorized A2A client submits a task
- **THEN** the agent responds with a protocol-conformant task/result or an explicit authorization denial

### Requirement: AF-REQ-014 — Controlled release
The factory SHALL permit release only after reproducible quality evidence, hard safety checks and necessary human approval.

#### Scenario: Holdout has not run
- **WHEN** a candidate passes training examples but no independent acceptance dataset is available
- **THEN** the release remains BLOCKED

### Requirement: AF-REQ-015 — Audit and reversible rollout
The factory SHALL record build provenance, decisions, approvals, change history and an operational rollback route.

#### Scenario: Post-release regression
- **WHEN** a canary agent violates a previously passed release constraint
- **THEN** automated policy suspends or rolls back that version and preserves audit evidence

### Requirement: AF-REQ-016 — Demonstrable reuse
The MVP SHALL assemble at least two distinct domain tasks from one factory core without changes to factory source code between builds.

#### Scenario: New task with different tools
- **WHEN** an authorized user provides a second valid BusinessTask referencing different approved tools
- **THEN** the factory generates a corresponding AgentSpec and executes independent acceptance cases

### Requirement: AF-REQ-017 — Optional evidence-based model training
The factory SHALL offer Soup/LoRA only as a gated experiment when suitable lawful training data and comparative benchmarks exist.

#### Scenario: No training dataset rights
- **WHEN** tenant data is not licensed for training
- **THEN** fine-tuning is disabled and the existing model is preserved

### Requirement: AF-REQ-018 — Portable durable implementation
The factory SHALL expose a runtime interface capable of comparing alternatives, including experimental Pi Durable, without coupling domain logic to runtime internals.

#### Scenario: Pi Durable unavailable
- **WHEN** an experimental durable adapter is not production ready
- **THEN** an approved alternative is usable without changing domain task contracts

### Requirement: AF-REQ-019 — Redacted observability
The factory SHALL trace tool calls, decisions, evaluations and optimizer versions while redacting secrets and restricting tenant access.

#### Scenario: Secret returned by tool
- **WHEN** a tool result includes an access token
- **THEN** stored traces redact its value and prevent access from other tenants

### Requirement: AF-REQ-020 — Security regression suite
The project SHALL maintain automated security checks for tool injection, side-effect authorization, network isolation and cross-tenant separation.

#### Scenario: Cross-tenant evaluation read
- **WHEN** a caller requests an evaluation from another tenant
- **THEN** the API denies access and emits a security audit event

### Requirement: AF-REQ-021 — Spec-to-test merge traceability
Each implemented behavior SHALL link its requirements and design decisions to tasks, tests and evidence prior to merge.

#### Scenario: Implementation without proof
- **WHEN** a feature PR has unchecked acceptance tests or missing requirement mapping
- **THEN** required checks fail and the PR cannot be considered releasable

### Requirement: AF-REQ-022 — Consent and escalation
The platform SHALL obtain authorization for proprietary data use and escalate unavailable information or privileged actions to an appropriate human decision maker.

#### Scenario: Unknown product substitution
- **WHEN** candidate chemical substitutions have no verified equivalence or approval
- **THEN** the agent requests an authorized domain review rather than treating them as interchangeable
