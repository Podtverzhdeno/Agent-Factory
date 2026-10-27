## ADDED Requirements

### Requirement: AF-REQ-003 — Trusted versioned capability registry
The factory SHALL maintain manifests for eligible tools, MCP servers, skills and API adapters with versions, typed schemas, scopes, side effects, fixture tests and a responsible owner.

#### Scenario: Untrusted tool discovery
- **WHEN** an unknown MCP service is discovered through metadata or user input
- **THEN** it remains unavailable for automatic execution until its manifest and permissions are reviewed

### Requirement: AF-REQ-004 — Permissions enforced independently of the LLM
The factory SHALL enforce tenant grants, approved endpoint boundaries and side-effect policy outside prompt instructions.

#### Scenario: Unauthorized order creation
- **WHEN** a generated agent asks for an order-creation tool with read-only permission
- **THEN** the adapter denies the call and records an auditable policy violation

### Requirement: AF-REQ-005 — Minimum sufficient tool selection
The factory SHALL select only capabilities justified by explicit task requirements and compatibility, optimizing for least authority and operational cost under quality constraints.

#### Scenario: Lookup-only objective
- **WHEN** the task only requires catalog matching
- **THEN** the generated AgentSpec excludes payment and destructive ERP tools

### Requirement: AF-REQ-006 — Reproducible agent assembly
The factory SHALL produce an immutable versioned AgentSpec pinning prompt, model, harness, tool versions, grants, state policy and A2A metadata.

#### Scenario: Same spec and registry versions
- **WHEN** assembly is repeated with the same task, policy, registry and model configuration
- **THEN** the factory records a reproducible artifact manifest and explains any nondeterministic outputs
