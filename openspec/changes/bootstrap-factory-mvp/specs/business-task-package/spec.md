## ADDED Requirements

### Requirement: AF-REQ-024 — Structured versioned Business Task Package
The factory SHALL accept a versioned, typed business-task package including objective, process, input/output contracts, business rules, permissions, attachment references, cost/attempt limits and measurable acceptance criteria.

#### Scenario: Business goal with sufficient context
- **WHEN** the user submits a package with objective, typed I/O, permissions, applicable rules and testable success conditions
- **THEN** the task service stores an immutable revision capable of producing a reproducible AgentSpec input

#### Scenario: Vague business prompt
- **WHEN** the submitted task omits essential I/O or business success criteria
- **THEN** readiness is BLOCKED with actionable clarification questions rather than guessed business requirements

### Requirement: AF-REQ-025 — Typed and permissioned artifact references
The factory SHALL accept uploaded and linked files with declared purpose, rights, tenant ownership, immutable version and digest, provenance and access-control scope. Binary files SHALL be stored in artifact storage rather than database blobs or Kafka events.

#### Scenario: Input Excel and gold output document
- **WHEN** an authorized user uploads an XLSX business request, approved SOP and paired expected output
- **THEN** each artifact is versioned and linked to the task with its explicit distinct role and tenant-bound access policy

#### Scenario: Unauthorized attachment
- **WHEN** an agent or service requests another tenant's file
- **THEN** the artifact service denies the request and logs the attempted access

### Requirement: AF-REQ-026 — Safe multimodal/document ingestion
The factory SHALL safely process common business document formats (XLSX, CSV, PDF, DOCX, JSON/API schemas), preserve provenance of extracted facts and expose extraction limitations or conflicting rules.

#### Scenario: Spreadsheet with multiple sheets
- **WHEN** an XLSX attachment includes multiple sheets, tables, formulas and units
- **THEN** the ingestion worker returns structured, referenced content without executing macros

#### Scenario: Untrusted document content
- **WHEN** an uploaded file contains malicious code, prompt injection or unreliable extraction
- **THEN** the system blocks unsafe execution and flags uncertain information for review

### Requirement: AF-REQ-027 — Grounded instructions and output artifacts
The Builder SHALL derive proposed system instructions, graph steps, tool needs and output schemas from approved rules, typed inputs/outputs, templates and explicitly labeled examples, with versioned source references.

#### Scenario: Sample quotation with required template
- **WHEN** a task contains a verified quotation XLSX output template, approved SOP and matching catalog operations
- **THEN** Builder generates a candidate AgentSpec that preserves required fields, selects approved read-only capabilities and records why they were chosen

#### Scenario: Conflicting examples and policy
- **WHEN** an example output contradicts an approved business rule
- **THEN** the factory requests business-owner clarification and does not silently privilege an unreviewed example

### Requirement: AF-REQ-028 — Independent evaluation data segregation
The factory SHALL separate approved build examples, optimizer tuning and validation cases from sealed acceptance holdouts, including output files and business effect oracles. Builder and GEPARD SHALL NOT read hidden evaluation answers.

#### Scenario: Optimizer requests a sealed answer
- **WHEN** GEPARD or Builder requests a SEALED_HOLDOUT artifact or its gold response
- **THEN** access is denied even if its artifact ID is known

#### Scenario: Known sample and hidden acceptance tests overlap
- **WHEN** an input, gold file or near-duplicate appears in both tuning and holdout
- **THEN** the evaluator flags contamination and excludes the duplicate from independent release evidence

### Requirement: AF-REQ-029 — Explainable capability matching and gaps
The Builder SHALL map workflow steps to required capabilities and compare them with Tool/MCP Registry manifests, selecting the minimum authorized compatible set and reporting missing integrations, data or permissions.

#### Scenario: Spreadsheet workflow with external catalog
- **WHEN** a task requires reading XLSX and querying an authorized product catalog
- **THEN** the assembly plan explains selecting file parsing and catalog lookup capabilities, without unrelated payment tools

#### Scenario: Missing catalog integration
- **WHEN** no authorized tool can perform a mandatory business operation
- **THEN** the build is BLOCKED with a precise missing-capability and access request, not a fabricated tool

### Requirement: AF-REQ-030 — Readiness, immutable build snapshots and change propagation
The factory SHALL require validated task readiness before builds, freeze a versioned Task Package snapshot and rerun affected capability selection and evaluations when the owner changes authoritative files, output templates or rules.

#### Scenario: Updated approved SOP
- **WHEN** the business owner updates an approved process rule after the agent was built
- **THEN** a new package revision is created, dependent agent candidates are flagged for re-evaluation and no serving agent is silently mutated

#### Scenario: Incomplete file ingestion
- **WHEN** a required input file cannot be parsed or lacks permission to process
- **THEN** the task remains REQUIRES_CLARIFICATION or BLOCKED and no verified release is issued
