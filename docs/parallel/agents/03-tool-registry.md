# AGENT 03 — Trusted Tool / MCP Registry

**Branch:** agent/03-tool-registry
**You own only:** \`services/tool-mcp-registry/**\`, \`tests/tool-registry/**\`
**Stack:** Java 21+ Spring Boot; registry-owned PostgreSQL schema, REST/OpenAPI and typed manifest schemas.
**Relevant requirements:** AF-REQ-003/004, AF-REQ-020 (tool security), AF-REQ-029, AF-REQ-041 (compatibility/description validation).

## One independently owned task

Deliver a **trusted, versioned catalogue of tools and MCP operations**, plus safe minimal capability matching. Never run untrusted MCP servers or grant capabilities implicitly. Agent 04 may use mocked registry responses until this contract is ready.

## Owned API + models

Versioned \`ToolManifest\` containing tool ID, semantic version, digest, typed arguments/result schema refs, transport, side-effect category, risk, allowlisted endpoint ref, health, required scopes, tenant availability, provenance, approved model-facing description and approval status.

Proposed REST methods: register draft manifest, validate/approve immutable version, lookup eligible capabilities, list a tenant's approved operations and report explicit denied matches. Return shape should match CONTRACTS_V0. Handle security through caller identity, independent of prompt claims.

## Deliverables

1. Tool/MCP manifest schema and validation, prohibition of secret embedding and SSRF risk surfaces.
2. Immutable approved manifest versioning and capability/operation lookup; missing permission returns a typed denial.
3. Deterministic minimal authorized capability set algorithm or service operation (with duplicate/incompatible capability policies). If Builder later chooses minimal set, expose ordered eligible candidates with explanation, not silent high-privilege picks.
4. Contract/mocking fixtures for read_xlsx, catalog_lookup, write_xlsx plus a prohibited payment tool.
5. Tests for version pinning, invalid schema, malicious description, wrong tenant, unverifiable MCP endpoint, permission escalation and impossible capability.
6. OpenAPI + README + executable local tests + PR.

## Acceptance

Given a synthetic RFQ requiring read_xlsx, catalog_lookup and write_xlsx, return three authorized compatible capability implementations; the unrelated payment operation must never appear. On absent scoped catalog access return a structured blocker instead of fabricating a tool. Tests run without Builder.

## Exclusions

Do not implement document ingestion, Builder, external live tool execution, Orchestrator state or GEPARD. Registry verifies descriptions but does not perform unreviewed runtime prompt optimizations.

## Copy/paste launch prompt

> Build only workstream **03 Trusted Tool/MCP Registry**, on **agent/03-tool-registry**. Read \`AGENTS.md\`, \`docs/parallel/README.md\`, \`docs/parallel/CONTRACTS_V0.md\` and this task file. You alone may edit \`services/tool-mcp-registry/**\` and \`tests/tool-registry/**\`; all other paths are read-only. Implement schema-based manifest registry and authorization-aware capability lookup with synthetic MCP fixtures and negative security tests; open PR targeting \`docs/sdd-foundation-mvp\` with actual test output. Do not claim ADR approval or working external integrations.
