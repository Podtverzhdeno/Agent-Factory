# Tasks — bootstrap-factory-mvp

**Status: all implementation tasks OPEN.** This PR establishes specifications only. Mark [x] after cited executable proof.

## Owner architecture prerequisite

- [ ] T00 — Owner @Podtverzhdeno personally specifies microservice boundaries and approves ADR-0002 with GitHub-verifiable evidence. Keep topology-dependent implementation BLOCKED until then.

## Business Task Package and files — prerequisite to usable Builder

- [ ] T18 (AF-REQ-024, AF-REQ-025) Implement versioned typed BusinessTaskPackage, artifact roles, ACL, immutable hashes and tenant-scoped S3-compatible upload references; tests: schema errors, rights, cross-tenant, corruption and version pinning.
- [ ] T19 (AF-REQ-026, AF-REQ-027) Implement safe async PDF/DOCX/XLSX/CSV and API-schema ingestion workers; preserve sheet/page/row provenance, pair examples and extract candidate instructions/output templates; tests: macros, malicious documents, corrupted files, ambiguity, output file structure.
- [ ] T20 (AF-REQ-028) Implement train/validation/hidden-holdout partitioning with Evaluation-owned vault and explicit access-control enforcement; tests: deny Builder/GEPARD, near-duplicate cases, holdout answer leakage.
- [ ] T21 (AF-REQ-029) Implement grounded capability mapping from approved workflow and files to Tool/MCP Registry, explain tool selection and block on missing permissions/capability; tests: minimum tool coverage, unused payment tools denied and missing integration blocker.
- [ ] T22 (AF-REQ-030) Implement intake READY readiness, owner-validated clarifications, immutable build snapshot, change invalidation and affected-agent re-evaluation; tests: changed SOP/template revision and stale build rejection.

## Business Task Package and file-based evidence

- [ ] T18 (AF-REQ-024, AF-REQ-025) Implement typed versioned BusinessTaskPackage, purpose-tagged artifact references, uploads, metadata, and tenant-scoped access tests.
- [ ] T19 (AF-REQ-026, AF-REQ-027) Implement safe PDF/DOCX/XLSX/CSV/OpenAPI parsing, provenance, paired examples, document output contracts, and ingestion tests.
- [ ] T20 (AF-REQ-028) Implement segregated training/validation/hidden-holdout storage and access tests.
- [ ] T21 (AF-REQ-029) Implement explainable workflow-to-tool matching and explicit missing-capability blockers.
- [ ] T22 (AF-REQ-030) Implement task readiness, immutable build snapshots, owner clarification workflow and change-triggered regression tests.

## P0 — specifications and contracts

- [ ] T01 (AF-REQ-001, AF-REQ-002) Implement validated BusinessTask and success-criteria models; tests: valid/invalid objectives, missing benchmarks and forbidden actions.
- [ ] T02 (AF-REQ-003, AF-REQ-004) Implement trusted Tool/MCP Registry + versioned manifest schemas; tests: malicious descriptions, invalid schemas, unauthorized endpoints.
- [ ] T03 (AF-REQ-005, AF-REQ-006) Implement minimal planner and immutable AgentSpec; tests: selection stability, zero unnecessary tools, incompatible tools rejected.
- [ ] T04 (AF-REQ-007) Implement sandbox runner with fake tools, per-tenant isolation and spend/step bounds; tests: budget limits, SSRF, tool-scope denial.
- [ ] T05 (AF-REQ-008, AF-REQ-009) Implement deterministic + independent evaluators with versioned dataset; tests: correct, false positive, safety-hard-gate and hidden holdout isolation.

## P1 — convergence and durable pilot

- [ ] T06 (AF-REQ-010, AF-REQ-011) Add repair controller and GEPARD optimizer adapter; tests: immutable baseline, prompt improvement, no-regression, max-attempts reached.
- [ ] T07 (AF-REQ-012) Add swappable durable checkpoint/resume adapter; tests: process kill, replay, duplicate effects and reconciliation.
- [ ] T08 (AF-REQ-013) Add official A2A SDK server/client adapter; tests: independent client invocation and denied unauthorized request.
- [ ] T09 (AF-REQ-014, AF-REQ-015) Implement approval workflow, versioned release, audit and rollback; tests: approval required and safety veto overrides score.
- [ ] T10 (AF-REQ-016) Build two distinct B2B task fixtures and automate no-code factory reconfiguration test; record comparative evidence.

## MVP gateway — owner requested

- [ ] T17 (AF-REQ-023) Integrate LiteLLM Proxy through ModelGateway port; configure its dedicated database, central provider credentials, model allowlists, per-tenant/agent budget tracking, rate limits, trace correlation and tests for unauthorized model access, exceeded budget, missing DB and provider failure. Do not expose provider credentials to agents or prompts.

## P2 — experiments (not release dependencies)

- [ ] T11 (AF-REQ-017) Benchmark Soup/LoRA against prompt-only and model-router baselines on a separate held-out dataset; assess cost per correct task including training and ops.
- [ ] T12 (AF-REQ-018) Compare Pi Durable with Python-native checkpoint/runtime alternative; record language boundary, failure semantics and operational overhead.

## Cross-cutting gates

- [ ] T13 (AF-REQ-019) Implement tracing and artifact provenance with secret redaction and retention controls.
- [ ] T14 (AF-REQ-020) Implement threat model and security/tenant/failure regression suite.
- [ ] T15 (AF-REQ-021) Build CI: SDD contract checks, lint/type/unit/integration, eval smoke, redaction scans, release evidence.
- [ ] T16 (AF-REQ-022) Document customer data rights, consent, manual blockers, human escalation and safe rollback.

## Evidence per completed task

Link the test command, CI run, commit SHA, fixture/dataset version, actual result and remaining limitations in PR. Failing or not-yet-run tests do not count.
