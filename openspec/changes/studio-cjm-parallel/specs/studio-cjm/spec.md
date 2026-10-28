# Studio Customer Journey, Operations, Charting and Parallel Delivery

## ADDED Requirements

### Requirement: AF-REQ-100 — Customer onboarding and workspace isolation
The Studio SHALL authenticate users via a trusted server-side session and authorize each tenant/workspace/entity/action independently. Workspace switches SHALL discard or partition previous tenant cache.
#### Scenario: Unauthorized cross-tenant deep link
- **GIVEN** user A lacks access to tenant B
- **WHEN** user A opens tenant B's agent/workflow/artifact URL, search or chart
- **THEN** the server refuses access without revealing tenant B's data or resource existence.

### Requirement: AF-REQ-101 — Guided task authoring
The Studio SHALL support a revisioned structured Business Task Package with business objective, inputs/outputs, rules, acceptance criteria, constraints, owner and save/resume.
#### Scenario: Conflicting draft edit
- **GIVEN** draft revision r1 is open in two tabs
- **WHEN** an outdated tab submits a change
- **THEN** optimistic concurrency rejects the update and the UI preserves unsaved input for user resolution.

### Requirement: AF-REQ-102 — Provenanced and purpose-tagged uploads
The Studio SHALL expose authorized document upload, classification, ingestion state, provenance and errors for applicable XLSX/PDF/DOCX/CSV/JSON/OpenAPI business inputs.
#### Scenario: Untrusted attachment
- **WHEN** an attachment fails type, malware, rights or parser checks
- **THEN** only that attachment is rejected and the business draft remains recoverable; unapproved content never reaches Builder.

### Requirement: AF-REQ-103 — Authorized integrations
The Studio SHALL display only Registry-eligible tools with operation/version, scope, risk, allowed effects and typed denials. It SHALL NOT itself grant permissions.
#### Scenario: Missing ERP grant
- **GIVEN** a task needs catalog:read
- **WHEN** the requester has no grant
- **THEN** readiness is blocked and the UI offers an authorized access request, not an implicit grant.

### Requirement: AF-REQ-104 — Immutable preflight
The Studio SHALL show missing requirements, require owner confirmation and bind an immutable READY task snapshot before build.
#### Scenario: Post-READY revision
- **WHEN** the owner edits a READY task
- **THEN** it creates a new revision requiring validation; the original build snapshot remains unchanged.

### Requirement: AF-REQ-105 — Idempotent build command and real timeline
The Studio SHALL issue an explicit authorized Orchestrator command and show real stage states, timestamps, blockers, operation receipt and source audit.
#### Scenario: Double click and server timeout
- **WHEN** the client submits or retries one build intent
- **THEN** the same idempotency scope cannot create duplicate semantic builds; no fabricated progress is displayed.

### Requirement: AF-REQ-106 — Real sandbox output and effect verification
The Studio SHALL display actual sandbox run outputs and distinguish internal effect reservations from independently verified external effects.
#### Scenario: Model falsely claims action
- **WHEN** an agent text says an ERP update succeeded but no external receipt exists
- **THEN** the UI indicates UNCONFIRMED and no dependent PASS or RELEASED claim is allowed.

### Requirement: AF-REQ-107 — Independent Evaluation quality
The Studio SHALL present Evaluation-owned status, dataset/sample provenance, safety veto, signed evidence availability, outcome and safe error findings without exposing sealed gold.
#### Scenario: Missing independent proof
- **WHEN** signed Runtime evidence or required gold is unavailable
- **THEN** evaluation is BLOCKED/INCONCLUSIVE/UNAVAILABLE, never fake PASSED.

### Requirement: AF-REQ-108 — Governed optimization
The Studio SHALL compare immutable baseline and proposed optimizer candidates with bounded attempts/cost, a real optimizer label and independent retest.
#### Scenario: Mock or regression
- **WHEN** only deterministic mock GEPARD is connected or candidate regresses
- **THEN** the UI labels synthetic/mock evidence and cannot promote the candidate as a measured live improvement.

### Requirement: AF-REQ-109 — Source-authoritative version/release/rollback
The Studio SHALL show immutable AgentSpec/version hashes, independent checks, approvals and real source-owned promotion/rollback state.
#### Scenario: Blocked promotion
- **WHEN** actor lacks scope, evaluation failed or deployment unavailable
- **THEN** release remains unavailable, and an optimistic browser action never changes it to RELEASED.

### Requirement: AF-REQ-110 — Clear actionable workflow recovery
The Studio SHALL provide typed error/required-action, correct responsible actor, stale timestamp, safe retry or escalation per workflow.
#### Scenario: Source outage
- **WHEN** a service becomes unavailable during creation
- **THEN** the last verified state is shown as stale, with no false terminal state and a recoverable link to the workflow.

### Requirement: AF-REQ-111 — Agent Mission Control
The Studio SHALL show authorized agent objective, current version, environment, capabilities, last runs, quality evidence, actions and contextual deep links.
#### Scenario: Sandbox/prod mismatch
- **WHEN** a user switches between sandbox and production
- **THEN** the UI clearly identifies environment and disallows sandbox candidate as production release.

### Requirement: AF-REQ-112 — Full Operator Console
The target product SHALL have **15 privileged modules**: Fleet, Workflows/Queues, Builder/AgentSpecs, Runtime/Checkpoints, Registry, Connectors/Secrets, Intake/Artifacts, Evaluation/Holdouts, GEPARD, Models/LiteLLM, A2A/Bilateral, Releases/AgentStore, Observability, Security/Tenants/Audit, Incidents/Alerts/SLO.
#### Scenario: One upstream is missing
- **WHEN** an operator opens a module with no deployed source
- **THEN** it shows a truthful NOT_CONNECTED or unavailable state, no synthetic data and no inert privileged mutation disguised as working.

### Requirement: AF-REQ-113 — Operator privilege, approvals and audit
Every mutating Ops operation SHALL undergo owner-service authorization, reason and audit; high-impact actions SHALL use explicit confirmation and required approvals.
#### Scenario: Operator without a specific scope
- **WHEN** a general operator attempts key rotation, manifest revoke or release without the grant
- **THEN** the action is denied and cannot be invoked through a direct HTTP request.

### Requirement: AF-REQ-114 — Source-backed shared chart kit
The target Studio SHALL provide a reusable typed set of **15 chart templates** (trend, stacked bar, error bar, scatter, heatmap, funnel, timeline, waterfall/flame, Sankey, treemap, histogram/box, gauge, dependency graph, status donut, A2A sequence).
#### Scenario: Missing or incomplete metrics
- **WHEN** a chart source lacks timestamps, denominator or verified series
- **THEN** it renders unavailable/partial with source and an accessible fallback table, not fabricated values.

### Requirement: AF-REQ-115 — Chart data isolation and performance
Chart aggregations SHALL be tenant-scoped, server-aggregated/paginated where needed, and avoid sending raw high-cardinality traces or hidden cases to browsers.
#### Scenario: Large traces
- **WHEN** an operator explores a long run
- **THEN** rendering remains bounded and uses lazy loading/aggregation without cross-tenant visibility.

### Requirement: AF-REQ-116 — Dual-company collaborative builder
The target advanced Studio SHALL support separate authorized Business Task Packages, independent Builder/AgentSpecs, distinct sandboxes, shared permitted A2A interactions and version-pinned experiments.
#### Scenario: Partner has not consented
- **GIVEN** company A created a bilateral scenario
- **WHEN** company B has not approved participation/disclosure
- **THEN** no cross-tenant build, shared trace or joint evaluation may start.

### Requirement: AF-REQ-117 — Independent bilateral evaluation and promotion
The Studio SHALL show separate Evaluation A, Evaluation B and joint result; candidate cross-play A1×B0, A0×B1, A1×B1; each tenant retains release authority.
#### Scenario: One party fails its safety gate
- **WHEN** joint metric improves but B safety gate fails
- **THEN** B cannot be promoted and A/B private evidence stays separate.

### Requirement: AF-REQ-118 — Bilateral consent withdrawal and privacy
The Studio SHALL allow revocation of sharing authority and show redacted partner interaction history according to retention.
#### Scenario: Mid-experiment consent revoked
- **WHEN** partner B withdraws consent
- **THEN** future shared runs stop and neither side can view newly unauthorized data.

### Requirement: AF-REQ-119 — Ideas-only visual graph editing
The target roadmap SHALL record a future LangGraph visual editor using typed graph IR, validation, immutable candidate and quality gate, but SHALL NOT expose functional editing before backend compilation and security exist.
#### Scenario: Current release
- **WHEN** a user opens the editor idea
- **THEN** it is explicitly labelled planned with no enabled save/deploy/run action.

### Requirement: AF-REQ-120 — Ideas-only microfrontends
The architecture roadmap SHALL describe possible route-level frontend decomposition with shared identity/contract/design-token/security boundaries and no initial Module Federation implementation.
#### Scenario: Current deployment
- **WHEN** the Studio runs one modular app
- **THEN** it does not require independent microfrontend build/deployment for normal operation.

### Requirement: AF-REQ-121 — Dynamic capability truth
The BFF SHALL distinguish product scope, delivery phase, tested evidence, deployed service status, tenant entitlement and role authorization for each feature.
#### Scenario: Static catalog includes bilateral editor
- **WHEN** the backend lacks bilateral evaluation or graph compilation
- **THEN** the UI cannot enable those operations solely from a static configuration file.

### Requirement: AF-REQ-122 — API version safety and unknown states
The UI SHALL handle service schema revisions and unknown enums with restrictive fallback, source stamp, error code and no privileged action.
#### Scenario: Backend introduces a new terminal value
- **WHEN** the frontend receives an unrecognized release state
- **THEN** it shows unsupported state rather than assigning RELEASED/PASSED.

### Requirement: AF-REQ-123 — Accessibility and RU/EN
The UI SHALL support keyboard workflows, semantic content, reduced motion, clear focus, accessible chart tables, screen reader status notifications and RU/EN localization.
#### Scenario: Keyboard-only business task
- **WHEN** user navigates upload, error resolution and approval dialogs without pointer
- **THEN** essential functions remain accessible and focus remains predictable.

### Requirement: AF-REQ-124 — Parallel implementation isolation
Coding teams SHALL own disjoint frontend paths, freeze shared contract, avoid cross-feature internal imports and hand integration to one owner.
#### Scenario: Agent attempts unowned change
- **WHEN** a feature PR touches central OpenAPI, another feature directory, root manifest or common layout
- **THEN** CI/Integrator rejects it until ownership is resolved; no silent merge conflict.

### Requirement: AF-REQ-125 — Integrated E2E gate with evidence
No feature SHALL be marked integrated without pinned-revision contract, role/tenant security, negative state and multi-service browser E2E on approved synthetic fixtures.
#### Scenario: Only design/lint passes
- **WHEN** a PR has successful docs validation but no real cross-service test
- **THEN** feature stays DESIGN/COMPONENT level and cannot be labelled production ready.


### Requirement: AF-REQ-126 — Visible exclusive task claims
Each independently assignable frontend task SHALL have one live coordination record with actor identity, task ID, UTC claimed_at, status, lease generation, current branch, base revision and PR references; claims SHALL be granted through a single-writer arbitration mechanism, not inferred from comments alone.
#### Scenario: Two agents claim the same task
- **GIVEN** two authorized agents observe one AVAILABLE task
- **WHEN** both submit a claim concurrently
- **THEN** at most one claim is granted and both agents can read the current owner, issue and lease generation.

### Requirement: AF-REQ-127 — Durable progress and liveness audit
Agents SHALL publish source-attributed append-only events for claim, heartbeat, meaningful progress with code/test evidence, blocked state, review, release and handoff. Activity, last meaningful progress and logical status timestamps SHALL be tracked separately.
#### Scenario: Fake progress heartbeat
- **GIVEN** an agent remains IN_PROGRESS for two hours with no code/spec/test evidence
- **WHEN** it submits only heartbeats or generic “working” messages
- **THEN** last_heartbeat_at may advance, but last_progress_at does not, and task becomes STALE_CANDIDATE.

### Requirement: AF-REQ-128 — Stale detection and free-task preference
The scheduler SHALL treat >120 minutes without verified meaningful progress while IN_PROGRESS as a stale REVIEW signal, not abandonment. Before takeover, it SHALL prefer compatible AVAILABLE tasks with prerequisites and file ownership satisfied.
#### Scenario: Stale and free work coexist
- **GIVEN** one stale task and one compatible AVAILABLE task
- **WHEN** an unoccupied agent selects next work
- **THEN** the free task is claimed first and the stale task is not taken over automatically.

### Requirement: AF-REQ-129 — Evidence-based safe takeover
When no compatible free task exists, the coordinator SHALL inspect task Issue, branch, all matching PR states, latest commits, CI results, owner notification/grace, dependencies and partial work before granting a task-scoped reassignment. Critical releases/security tasks require human approval.
#### Scenario: Stale but active PR
- **GIVEN** last progress comment older than two hours, but a new test run/commit or merged PR demonstrates advancement
- **WHEN** another agent requests takeover
- **THEN** the coordinator reconciles actual progress and refuses takeover as abandoned work.
#### Scenario: Genuine stalled task
- **GIVEN** no compatible free task, no new work evidence, expired grace and independent coordinator approval
- **WHEN** a takeover is granted
- **THEN** prior generation is revoked, new owner receives generation+1, old PR/commits remain linked, and the reason, timestamps and remaining tasks are auditable.

### Requirement: AF-REQ-130 — Fencing and path-safe handoff
Ownership transfer SHALL NOT give broad permission to edit code outside the task's exclusive file scope or allow an old owner to continue acting on a revoked generation.
#### Scenario: Previous agent attempts to submit completion
- **GIVEN** STU-T05 was transferred from A03 to A04 with lease generation incremented
- **WHEN** A03's old generation submits progress or marks DONE
- **THEN** coordinator/CI refuses it, and A04 may change only the explicitly delegated paths for this task.

### Requirement: AF-REQ-131 — Reassignment reflected in canonical spec
A successful takeover SHALL record the previous agent and PR evidence, exact UTC last progress and takeover times, what remains unfinished, reason, new owner and generation in Issue event history and an integrator-controlled OpenSpec handoff note. No unverified completion is marked as done.
#### Scenario: No remaining free tasks
- **GIVEN** available tasks are exhausted and coordinator confirms stalled work after reviewing repo/PR
- **WHEN** another agent accepts reassigned work
- **THEN** recorded handoff states “previous work paused; remaining work resumed by new owner” with timestamp and supporting links; it MUST NOT claim nothing was done when unmerged useful work exists.
