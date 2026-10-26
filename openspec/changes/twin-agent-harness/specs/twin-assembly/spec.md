## ADDED Requirements

### Requirement: AF-REQ-038 — Two separate corporate builds
The factory SHALL accept two independent permissioned Business Task Package snapshots, correlate them within one bilateral workflow, and explicitly launch independently authorized Builder jobs while preserving each organization's data and approval boundary.

#### Scenario: Valid bilateral build
- **WHEN** A and B each approve a task snapshot for a common A2A test scenario
- **THEN** Orchestrator initiates two Builder jobs using one common Builder implementation and produces independent versioned AgentSpecs

#### Scenario: Partial build failure
- **WHEN** A's Builder job fails after B completes
- **THEN** B's artifact remains valid and tenant-owned while the bilateral release remains blocked until A passes

### Requirement: AF-REQ-039 — Initial durable and memory-aware harness
The Builder SHALL provision durable execution, per-thread short-term memory and independent tenant-scoped long-term memory policy at the initial assembly of each agent.

#### Scenario: Interrupted A2A operation
- **WHEN** a worker crashes during a multi-turn task after an authorized external operation
- **THEN** the agent resumes from LangGraph persisted state and reconciles idempotent effects without duplicate business execution

### Requirement: AF-REQ-040 — Safe versioned harness configuration
The factory SHALL version model, prompts, tool descriptions, tool/MCP grants, ReAct graph settings, retrieval, memory policy, checkpoint/retry policy and A2A metadata, with a separate allowlist of automatically optimizable fields.

#### Scenario: Optimizer attempts unauthorized permission change
- **WHEN** a prompt or harness optimization requests higher-risk tool permissions
- **THEN** policy denies automatic promotion and requires separate authorized grant review
