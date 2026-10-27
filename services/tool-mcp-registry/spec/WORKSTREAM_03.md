# Workstream 03 — local change proposal and evidence, not canonical OpenSpec amendment

> Status: PROPOSED/COMPONENT VERIFIED. This note stays in the owned module because `openspec/**` and the shared frozen contracts are read-only for parallel coding agents. The owner/integrator must incorporate any change into canonical OpenSpec after architecture review.

## Goal and requirements

- **AF-REQ-003/004** — Given a trusted, single-tenant draft manifest, WHEN an independent reviewer approves an immutable version, THEN the authorized Builder can discover its pinned digest; WHEN version is revoked, THEN no future selection or unrevocation is possible. Drafts and unknown endpoints are never eligible.
- **AF-REQ-020** — Given a tenant identity and externally issued scopes, WHEN selecting or publishing a tool, THEN any missing permission, cross-tenant availability, untrusted MCP endpoint, malicious model-facing description or undeclared effect is denied without granting rights.
- **AF-REQ-029** — Given RFQ `read_xlsx`, `catalog_lookup`, `write_xlsx` and `read/draft_file` allowed effects, WHEN Builder requests tools, THEN return the smallest covering authorized compatible set and explanations; if any capability is missing, return `BLOCKED` and typed denials. The payment operation must not appear.
- **AF-REQ-041** — Given a version-pinned ToolManifest, WHEN checking input and output payloads, THEN reject invalid required fields, unexpected attributes, invalid nested object/array element types, incompatible schema refs and cross-version mix.

## Proposed design / decisions (pending owner topology ratification)

- Ports: trusted schema/endpoint resolver provided to the pure Java domain constructor, authenticated `Caller` derived by an HTTP JWT boundary; persistence and reviewer identity are unresolved external ports. The domain MUST not load URLs, mint grants or import Spring/MCP.
- Domain: `ToolRegistry` orchestrates lifecycle/policy and in-memory audit; `PayloadShapeValidator` validates recursive shapes; `MinimumCapabilityCover` performs bounded exact set cover. REST/OpenAPI/Jackson/Spring Security are strictly adapters.
- Integrity: length-prefixed, sorted canonical content digest; manifest immutable per `(tenantId, toolId, version, operation)`; distinct tenants may use the same operation ID and version without collisions. Version state changes APPROVED → REVOKED only; new version required to republish.
- Security: separate maker/checker, scoped tenant and permission checks, no raw endpoints, deny-by-default HTTP. Rejection codes are stable. Observability/audit would use a future durable per-tenant store, not a shared database chosen without owner approval.
- Compatibility proposal: lower-case wire representation for `risk_level` and `side_effects` as in frozen v0; temporary uppercase read tolerance for old tests. `revoke` and `audit` are optional additional endpoints; `Selection` preserves the documented v0 fields.

## Test and change traceability

| Task | Pure-Java checks | HTTP tests | Gate |
|---|---|---|---|
| Registration / immutable version | duplicate, maker-checker, digest, cross-tenant and revoked state | register/approve/revoke | Java verified, HTTP pending Maven |
| Security / allowlist | SSRF, injected description, risk lowering, permissions, tenant isolation | mock JWT roles, decoder config | Java verified, HTTP pending Maven |
| Minimal covering set | exact 3-tool RFQ, 30 alternatives, conflicting operation versions, partial version pinning | `/select` with scoped JWT | Java verified, HTTP pending Maven |
| Typed schemas | wrong types, nested arrays, required/unknown properties, size/numeric bounds | `/payloads/validate` (pending) | Java verified, HTTP pending Maven |
| PostgreSQL/attestation/deployment | blocked | blocked | OWNER ADR-0002 pending |

## Architecture gate and roll forward

1. Owner personally ratifies service boundaries, data ownership, communication, auth and deployment in `docs/architecture/adr/0002-microservices.md` with GitHub-verifiable evidence.
2. After that: select PostgreSQL schema/migrations, tenant RLS and transactional audit/outbox, trusted endpoint attestation, schema artifact resolver, health reconciler, secrets-policy ownership.
3. Run Maven/JUnit, integration against a signed local JWKS issuer, concurrency and fault injection; performance and security review.
4. Wire Builder using pinned `registry_revision` and selected manifests; revalidate live permission/effect checks at runtime. Explicit human approval/idempotency for consequential effects.
5. Implement metrics, retention, backup/restore, rollback and independent production threat review. No release or check-off of T00/T21 before evidence.
