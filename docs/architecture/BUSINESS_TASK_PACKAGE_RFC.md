# RFC: Business Task Package (BTP) and file-backed agent creation

**Status:** assistant architecture proposal for owner review; NOT approved in ADR-0002.
**Why:** A CRUD record containing objective/description cannot reliably drive tool selection, harness instructions or real business acceptance. The factory needs a typed, immutable, evidence-linked build request.

## 1. Separation of responsibility

- Task Intake & Requirements (logical bounded context, **not yet an approved deployable service**): receives typed objectives, workflows, governance, output formats, uploaded artifact manifests, allowed external operations, success tests, permissions, owner-approved clarifications and versions.
- Artifact Ingestion (Python worker capability, **not necessarily a new microservice**): malware/type checks, extraction from PDF/DOCX/XLSX/CSV/JSON/HTML and images as needed, preserves page/sheet/cell/row provenance, identifies tables and attachments, blocks unsafe/unreadable files, returns normalized evidence with source references. OCR only if source has no extractable text and the customer permits it.
- Agent Builder: reads an **approved, ready** immutable BTP snapshot and only the artifacts granted to the builder, performs capability gap analysis, chooses approved tools, generates constrained AgentSpec + system instructions + graph/workflow configuration.
- Evaluation Service: holds independent acceptance cases, authorized business-effect verification and **hidden holdout** material; the Builder, Runtime and GEPARD may not read its private answers. An optimizer can see tune/validation outcomes, not holdout keys/answers.

**Owner architecture decision still open:** separate Java Spring Boot Task Intake service vs module within Factory Orchestrator; separate Python Document Ingestion workers vs subprocess within Builder. Separate bounded responsibility does not automatically imply an independent microservice.

## 2. Minimum package sections

| Section | Mandatory? | What it means | Builder use |
| --- | --- | --- | --- |
| identity / revision | yes | tenant, owner, task ID, immutable revision, source hashes | reproducible assembly |
| objective | yes | business problem, actor, expected outcome, business value | task decomposition |
| process | yes for multi-step | stages, decision rules, exceptional cases, deadlines, approval points | graph / harness instructions |
| inputs | yes | runtime input schema and accepted formats (structured text, uploaded file, email, API event), typical and edge-case samples | parsers, connectors, contracts |
| outputs | yes | output schema, document template, required proof or side effect, format (JSON/XLSX/PDF/DOCX/API action) | tools, renderer, validation |
| integration grants | when needed | systems, operations, endpoint references, scopes, sandbox/test endpoints | Registry matching; never invent access |
| business rules | yes | approved policy docs, authoritative SOP, prohibited shortcuts, source precedence | system instructions and runtime checks |
| artifacts | often | references to source files, kind, data usage rights, classification, versions | evidence extraction and examples |
| examples | strongly recommended | request, correct output, rationale, acceptable alternatives, label provenance | prompt candidates and tool plan |
| acceptance | yes | hard gates, golden cases, functional invariants, real side-effect checks and risk limits | independent Evaluation |
| limits | yes | allowed/forbidden actions, time/spend, privacy/retention, accuracy threshold and approval | access policy, build/optimization budget |
| unresolved | yes as needed | clarifications and conflicts with owner decisions | BLOCKED until answered |

### Runtime input vs build-time evidence

A **runtime input** is a new task the deployed agent will receive in production (for example a new RFQ XLSX). A **build-time attachment** is a reference artifact used to design/test the agent (for example historic RFQs, SOP and catalog schema). Never bake a customer's example RFQ into the prompt as if it were the current request.

## 3. File roles and anti-leak controls

Each file is stored in artifact storage with an immutable content hash, metadata and a **purpose**:

1. **BUSINESS_RULES** — approved standards, process instructions, regulatory and internal restrictions; may inform agent prompt and runtime retrieval if entitled.
2. **REFERENCE_KNOWLEDGE** — catalogs, product specifications, FAQ, API/OpenAPI, ERP schemas; choose between indexing for retrieval and dynamic tool access based on freshness, authority and scale.
3. **INPUT_EXAMPLE** — sample real requests (anonymized/authorized), may be seen by Builder for task understanding.
4. **SOLUTION_EXAMPLE** — owner-reviewed expected output files and execution traces paired to INPUT_EXAMPLE; can inform few-shot/harness/evaluator tuning.
5. **TUNING_CASE** — labeled cases allowed to GEPARD for prompt/tool/harness optimization.
6. **VALIDATION_CASE** — disjoint scenarios for candidate selection and regression checks.
7. **SEALED_HOLDOUT** — independent acceptance tasks with gold outputs/effects under Evaluation-only ACL; **Builder/GEPARD cannot retrieve these files, answers or their hidden rationale**. Do not expose per-case holdout feedback to optimizer loops.
8. **OUTPUT_TEMPLATE** — approved required structure, placeholders and formatting of DOCX/XLSX/PDF/JSON deliverables.
9. **CONNECTOR_CONTRACT** — REST OpenAPI/JSON Schema/MCP manifest, example request/responses, declared credentials/scopes. A spec document is not permission to call production.
10. **EXECUTION_EVIDENCE** — auditor-approved traces and side effects, retained only under policy.

Roles are explicit, never inferred from filename alone. One identical file cannot be silently placed in both tuning and holdout partitions. Files containing customer secrets/PII are redacted or access-controlled, never used for fine-tuning without explicit rights. Hashes and lineage identify duplicates and near-duplicates across partitions.

## 4. Intake / processing lifecycle

DRAFT -> UPLOADING -> INGESTING -> REQUIRES_CLARIFICATION (as needed) -> VALIDATED -> READY_FOR_BUILD -> SNAPSHOTTED -> BUILD_REQUESTED. A new version after READY creates a new immutable snapshot, new compatibility checks and new evaluation baseline.

Suggested API (contracts pending owner ADR):
- POST /v1/business-tasks: create draft, return task ID/version
- PUT /v1/business-tasks/{id}: update editable draft fields with optimistic concurrency
- POST /v1/business-tasks/{id}/attachments: issue scoped upload or register pre-existing artifact
- GET /v1/business-tasks/{id}/artifacts: list metadata, parsing/approval/usage status
- POST /v1/business-tasks/{id}/validate: perform schema, file and policy preflight, return missing-data questions
- POST /v1/business-tasks/{id}/ready: owner confirms rules and freezes a build snapshot
- POST /v1/builds: Orchestrator explicitly commands Builder with a snapshot ID; NEVER send full binary files via Kafka.

Use S3-compatible storage for object bytes and service-owned PostgreSQL for metadata, rights and workflow state. Short-lived tenant-scoped signed URLs or authorized artifact APIs for file access; do not expose durable public URLs, upload full files to event messages or let independent services mutate Task Intake tables.

## 5. Automated but grounded interpretation pipeline

**A. Preflight:** malware/zip-bomb/macro screening, MIME and extension detection, size/tenant quota, API/URL policy, rights to inspect/train, secrets/PII classification, hash, access label. Treat uploaded text as DATA, not executable instructions.

**B. Content processing:** extract structured text plus format-specific structure:
- XLSX: sheets, tables, header rows, formulas/results, units and merged cells; avoid executing arbitrary macros.
- PDF/DOCX: paragraphs/tables, pages/headings, text and provenance; visual analysis only when extraction fails or figure understanding matters.
- API OpenAPI / JSON Schema / MCP specs: normalize operation IDs, input/output schemas and declared scopes.
- Paired examples: link request ID to correct output and rationale; human can approve alternatives and exceptions.

**C. Evidence model:** each extracted assertion has an artifact ID, version, page/sheet/row/span, parser version, extraction confidence and authority grade; contradictions or uncertain business rules raise clarification instead of inventing facts.

**D. Requirement normalization:** generate draft structured requirements and candidate tool capabilities through LLM (via LiteLLM), run deterministic schema/policy validation and ask business owner to approve interpretation where significant ambiguity exists.

**E. Builder capability matching:** convert each work step to required input/output capability; query central Registry for tool/MCP candidates by supported operation, schemas, tenant grants, safety, side effect and availability. Choose minimum eligible set, explain WHY chosen and identify missing capability. Never silently write/build a new trusted integration from random uploaded code.

**F. Harness generation:** compile objective, authoritative business rules, source citations, error cases, workflow, tools and output constraints into versioned system prompt + LangGraph configuration; prompt is candidate and must be tested. Rules outrank historical examples; contradictions block promotion.

**G. Quality and optimization:** independent Evaluation executes gold and holdout fixtures against actual output files and auditable side effects. GEPARD may use only granted tune/validation material and sanitized diagnostics; new candidate is retested on a sealed holdout not iteratively exposed. Soup uses only separately licensed training examples.

## 6. Illustrative YAML package (NOT a deployed schema)

~~~yaml
schema_version: "0.1"
task_id: "rfq-chemical-001"
revision: 3
tenant_id: "demo-tenant"
objective:
  actor: "B2B sales specialist"
  desired_outcome: "Produce a reviewable chemical quotation from an RFQ"
  completion_definition: "A correctly matched, policy-compliant draft quotation file"
workflow:
  steps: [parse_rfq, resolve_products, verify_restrictions, calculate_quote, render_document]
  escalation:
    - when: "no exact product or verified substitute"
      action: "request_domain_expert"
inputs:
  - name: rfq
    media_types: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
    schema_ref: "artifact://schemas/rfq-v1"
outputs:
  - name: draft_quote
    media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    template_ref: "artifact://templates/quotation-v2"
business_rules:
  - artifact_ref: "artifact://approved/sop-v3"
integrations:
  - system: "product-catalog"
    required_capability: "search_by_cas_and_grade"
    allowed_effects: ["read"]
    credential_ref: "vault://demo/catalog-readonly"
attachments:
  - {artifact_ref: "artifact://examples/rfq-01", purpose: "INPUT_EXAMPLE"}
  - {artifact_ref: "artifact://examples/quote-01", purpose: "SOLUTION_EXAMPLE", paired_with: "artifact://examples/rfq-01"}
  - {artifact_ref: "artifact://eval/holdout-08", purpose: "SEALED_HOLDOUT", access: "evaluation-only"}
acceptance:
  checks:
    - "Every line is matched to a verified catalog entry or explicitly escalated"
    - "Final XLSX has all mandatory output fields and no unauthorized substitutions"
  safety_veto:
    - "No order placement, payment or automatic email sending"
limits:
  max_cost_usd_per_build: 15
  max_optimization_attempts: 5
~~~ 

The currency and threshold above are **illustrative, not approved product defaults**. In real interfaces sealed holdout references should be issued directly to Evaluation, not returned as downloadable artifacts to Builder or GEPARD.

## 7. Pilot acceptance tests

- XLSX request + SOP PDF + output XLSX template + approved examples produce correct minimal capability requests and correctly formatted output, preserving units/CAS/grade.
- Missing catalog access returns BLOCKED with integration grant needed; no fabricated matching tool.
- An invalid file, malicious macros, embedded prompt injection and tenant-crossing file references are rejected or safely isolated.
- Examples can contain mistakes; conflicting SOP and example triggers clarification; no silent override of approved rules.
- GEPARD cannot retrieve sealed holdout answers even when it supplies a known artifact ID.
- Changing a rule file or an output template increments snapshot version and triggers regression evaluation.
- Builder trace explains selected tool IDs and why unnecessary high-privilege tools were excluded.
- Generated file is checked structurally and against expected business result; an LLM stating "done" does not satisfy Evaluation.

## 8. Architecture questions for owner

1. Do you want **Business Task / Requirements** and **Document Ingestion** as two independently deployed services, or one Java service with horizontally scalable Python document-processing workers? Proposal: separate processing workers, but reserve service boundary approval for ADR-0002.
2. Must the user explicitly label files as rules/examples/templates/holdout, or should factory auto-suggest roles and require confirmation before READY? Proposal: automatic suggestion + explicit approval for security-critical roles.
3. Should a business expert author criteria manually, or can the factory draft them from examples then require owner sign-off? Proposal: draft automatically but never invent hidden gold acceptance truth without review.
4. How are holdout suites collected and protected for the initial pilot? Need permissioned, independently labeled new cases and a testing process avoiding answer leakage.
