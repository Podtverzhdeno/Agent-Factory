## ADDED Requirements

### Requirement: AF-REQ-007 — Isolated and budgeted execution
The factory SHALL execute candidate agents in a sandbox subject to tenant, network, time, step and cost limits.

#### Scenario: Malicious tool output
- **WHEN** an MCP response tries to inject instructions to read credentials or exfiltrate data
- **THEN** the agent runtime denies the forbidden effect and logs the attempt

### Requirement: AF-REQ-008 — Independent business evaluation
The factory SHALL verify outputs and authorized external effects against versioned business criteria rather than relying only on the candidate agent's self-evaluation.

#### Scenario: Plausible response without required action
- **WHEN** an agent asserts task completion but the expected audited tool effect is absent
- **THEN** the evaluation marks the operation FAILED

### Requirement: AF-REQ-009 — Hard safety and regression gates
The factory SHALL fail closed on critical safety violations and protect held-out evaluations from optimizer overfitting.

#### Scenario: Improved average score but unauthorized write
- **WHEN** an optimization improves task accuracy but performs an unauthorized write
- **THEN** it fails regardless of overall score and is not eligible for release

### Requirement: AF-REQ-010 — Bounded diagnosis and repair
The factory SHALL classify failures and attempt permitted repairs under explicit attempt, time and spend budgets, recording each change.

#### Scenario: No approved connector exists
- **WHEN** available tool alternatives cannot satisfy the required operation
- **THEN** the repair controller stops with BLOCKED and a precise missing-capability request

### Requirement: AF-REQ-011 — GEPARD prompt and harness optimization
The factory SHALL permit sandboxed prompt/harness improvement using an immutable baseline, logged candidates, independent validation and rollback.

#### Scenario: Prompt candidate regresses tool reliability
- **WHEN** a GEPARD candidate improves textual quality but reduces required tool-call correctness
- **THEN** the factory rejects the candidate and preserves the baseline
