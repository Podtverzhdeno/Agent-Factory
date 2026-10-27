# AGENT 02 — Business Task & Artifact Ingestion

**Branch:** agent/02-business-task
**You own only:** \`services/business-task/**\`, \`services/document-ingestion/**\`, \`tests/business-task/**\`
**Stack:** Spring Boot (task metadata/ACL/versioning), Python processors/workers (PDF/DOCX/XLSX/CSV/JSON/OpenAPI), PostgreSQL metadata, S3-compatible object store port. Worker deployment boundary remains proposed pending owner ADR.
**Relevant requirements:** AF-REQ-001/002, AF-REQ-022, AF-REQ-024/025/026/027/030.

## One independently owned task

Build the **versioned, permission-controlled Business Task Package** intake domain and safe file normalization pipeline so Builder needs only an immutable READY snapshot. Do not implement Builder or quality grader. User uploads business description, SOP, templates, paired examples and tool/API docs. Every artifact has explicit purpose, tenant, hash, rights, version and provenance.

## Owned contracts

Provide \`POST /v1/business-tasks\`, draft update with optimistic concurrency, scoped artifact upload registration, parse job/status, validate/clarify, and freeze READY snapshot; \`GET /internal/business-task-snapshots/{id}\` must check authorized tenant and return the \`TaskSnapshot\` shape from CONTRACTS_V0. Separate all eval-only holdout materials: do NOT serve them to Builder/GEPARD/Runtime; workstream 05 owns sealed gold.

## Deliverables

1. Typed Business Task Package (objective, process, inputs, outputs, examples, constraints, allowed effects, acceptance policy, permissions and artifact refs).
2. Artifact metadata store port, S3 ref port and safe fixtures. No document bytes stored in Kafka or long-lived public URLs.
3. Parser interfaces + practical extractors for XLSX (sheets/headers/formulas/units), DOCX/PDF (paragraphs/tables/page refs), CSV and OpenAPI/JSON Schema, with provenance (page/sheet/row/hash/parser version).
4. Validation: source contradictions/undefined goal/unsupported file/unknown permissions -> \`REQUIRES_CLARIFICATION\` or \`BLOCKED\`; cannot invent requirements.
5. Ready snapshot immutability; updates increment version and invalidate stale references.
6. Security tests: corrupted/oversize files, macro execution forbidden, prompt injection treated as data, unauthorized tenant, unsanitized secrets, incomplete parsing. Use synthetic files, no real customer records.
7. Local reproducible tests and your own PR.

## Acceptance

A synthetic RFQ XLSX + SOP DOCX/PDF + quotation template and one paired example yield a READY, versioned Task Snapshot with trustworthy artifact provenance; a malicious/contradictory or missing-rights example does not. No other services need to exist for tests.

## Exclusions

Do not choose tools/MCP (03), generate AgentSpec (04), certify quality/holdout (05), or own Orchestrator (01). Do not silently create a separate deployed ingestion microservice as a settled ADR.

## Copy/paste launch prompt

> Implement only Agent Factory workstream **02 Business Task** on branch **agent/02-business-task**. Read \`AGENTS.md\`, \`docs/parallel/README.md\`, \`docs/parallel/CONTRACTS_V0.md\`, \`docs/architecture/BUSINESS_TASK_PACKAGE_RFC.md\`, and this task file. Restrict all edits to \`services/business-task/**\`, \`services/document-ingestion/**\`, \`tests/business-task/**\`. Implement versioned BTP intake + safe file ingestion with mocked object storage, independent component tests, exact acceptance evidence and a PR against \`docs/sdd-foundation-mvp\`. Respect the pending owner ADR, shared read-only contracts and tenant/holdout boundaries.
