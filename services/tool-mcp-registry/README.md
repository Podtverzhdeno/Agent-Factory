# Trusted Tool/MCP Registry — Agent 03

**State:** contract-first component with verified pure-Java domain/security tests. HTTP adapter tests are written but **not executed** in this environment (Maven not installed). Owner ADR-0002 still **PENDING**. No production service, external MCP runtime, production credentials, or PostgreSQL topology has been approved or deployed.

## Scope and boundaries

- Owned by workstream 03 only: `services/tool-mcp-registry/**` and `tests/tool-registry/**`.
- `ToolRegistry`: tenant-local draft, maker–checker approval, irreversible per-version revocation, immutable content digests, append-only in-memory audit, authorized discovery.
- `MinimumCapabilityCover`: exact cardinality minimum among authorized candidates; tie-break by risk, **distinct scope union**, effects and stable identifiers. Same tool cannot contribute different versions to a selection. Fails closed when constraints or search budget make selection unverifiable.
- `PayloadShapeValidator`: recursive strict *typed shape subset*, not full JSON Schema. Typed arrays/items and objects, required fields, no undeclared attributes, bounded depth/size, finite numeric values. Schemas are provided out-of-band by the trusted fixture registry.
- `RegistryApi`: experimental authenticated REST boundary; no running external MCP connections, network enumeration, payments, files or agent building.
- `RegistrySecurity`: deny all unless registry-specific issuer, JWKS URI and audience are configured; HTTPS same-host JWT/JWKS, no numeric IP or internal/local domain, no URL embedded credentials; issuer and audience checked by JWT decoder. Runtime egress restrictions must still protect against DNS rebinding.
- `RegistryJsonConfig`: transport contract uses snake_case keys, lowercase risk/effects (`low`, `read`, `draft_file`), strict unknown-field rejection. Uppercase risk/effect inputs are temporarily accepted for backwards compatibility; transport remains uppercase `MCP`/`LOCAL`.

## Invariants

1. **Tenant never comes from request body for authorization.** Only the externally validated JWT's `tenant_id` is used. A registrar can register a tool **only for exactly their own tenant**; no cross-tenant self-service publication. Registry keys include tenant_id; different tenants may register identical (tool_id, version, operation) independently. Cross-tenant manifests do not appear in selection candidates or typed denial reasons at all; audit/revision are tenant-scoped.
2. **No automatic grants.** JWT `scope` must independently contain `registry:*` and every tool's required scope. Even if allowed, a tool is not executed here; Builder receives a version/digest/scopes *binding proposal*, not credentials or runtime authority.
3. **Approval requires two distinct subjects** (`registry:register` creator and `registry:approve` reviewer); immutable manifest version cannot be replaced. Revocation is irreversible; publish another version to restore eligibility.
4. **No unverified endpoints.** `endpoint_ref` and provenance must come from *independently preconfigured* trusted reference sets, never from self-reported author text. Default Spring configuration contains **no trust roots**, so nobody can publish a tool until owner-ratified trust bootstrap exists. Tests supply synthetic refs only in test fixtures. An approved endpoint reference is not itself live attestation, never a caller-provided URL. No MCP server installation, health probe or raw secret access.
5. **Selection uses all gates**, in order: tenant, approval, scopes, allowed effects, maximum risk, known health, pinned version (only for explicitly pinned tool IDs), expected input/output schema-ref compatibility, version consistency across operations, then exact set cover. Impossible coverage is BLOCKED with machine-readable reasons.
6. **Manifest digests are content-integrity hashes**, not signatures; provenance/health/allowlist fixture maps currently are not cryptographically attested. Original schema references are illustrative; approved artifact revisions and independent source attestation are required before production.
7. **Hard boundaries:** payment/destructive manifests are at least CRITICAL and require explicit caller scopes/effects; downstream Runtime must additionally enforce explicit human approvals and idempotent side effects. Registry alone cannot establish safe execution.

## Run executable tests

From repo root:

```bash
bash tests/tool-registry/run.sh
```

Executed with OpenJDK 21 and `javac -Xlint:all -Werror`:

```text
PASS: 40 registry assertions across lifecycle, deterministic cover, tenant/scopes, risk/effects, schema, SSRF, versioning and injection
PASS: 50 additional registry security and lifecycle assertions
PASS: 500 deterministic property cases agree with independent exhaustive cover oracle
PASS: concurrent registrations linearize to one immutable manifest, one approval and one revocation
```

HTTP test command (**not run locally**):

```bash
mvn -f services/tool-mcp-registry/pom.xml test
```

It includes default-deny, mock-JWT route authorization and maker/checker/revocation, unknown-property handling, and JWT issuer/JWKS configuration rejection. Mock-JWT tests do not prove a live OIDC trust chain: independent signing/JWKS rotation, revocation and resource-server integration tests remain required.

## Example selection

**Prerequisites:** synthetic manifests registered and approved by two different principals. `tenant-a` Builder JWT includes `registry:lookup xlsx:read catalog:read xlsx:draft` scopes.

```json
{
  "required_capabilities": ["read_xlsx", "catalog_lookup", "write_xlsx"],
  "allowed_effects": ["read", "draft_file"],
  "max_risk": "low",
  "pinned_versions": {},
  "expected_schemas": {}
}
```

Result is exactly `xlsx.read`, `catalog.lookup`, `xlsx.write`, each with pinned version and manifest digest. `payments.charge` does not appear. Remove `catalog:read` and result becomes `BLOCKED` with `MISSING_PERMISSION`. Unsafe payment or schema mismatch also yields explicit blocker, never speculative permission.

## APIs

| Method | Route | Required JWT scope |
|---|---|---|
| POST | `/v0/registry/manifests` | `registry:register` |
| POST | `/v0/registry/manifests/{toolId}/{version}/{operation}/approve` | `registry:approve` |
| POST | `/v0/registry/manifests/{toolId}/{version}/{operation}/revoke` | `registry:approve` |
| GET | `/v0/registry/manifests` | `registry:lookup` + tool-specific scopes |
| GET | `/v0/registry/audit` | `registry:audit` |
| POST | `/v0/registry/select` | `registry:lookup` + tool-specific scopes |
| POST | `/v0/registry/payloads/validate` | `registry:lookup` + tool-specific scopes |

See `openapi.yaml` and [`SECURITY_REVIEW.md`](SECURITY_REVIEW.md). The URI and API contracts are *proposals* until owner approval; this is not an approved deployment topology.

## Threat model and unresolved gates

| Threat | Current control | Remaining work |
|---|---|---|
| Unknown MCP, SSRF and credential exfiltration | No network/MCP execution, strict artifact endpoint allowlist, description filter | Independent attestation, managed egress and DNS rebinding defense, policy enforcement at Runtime |
| Cross-tenant sharing/leaks | JWT tenant-only auth, single-tenant registrar, redacted wrong-tenant denials, tenant revision/audit | Auth service integration, multi-tenant database RLS, pen test |
| Permission escalation | Never mint scopes, compare issuer scopes vs manifest requiredScopes, risk/effect gates | Separate authorization service and Runtime enforcement on every invocation |
| Supply-chain/provenance forgery | Dual-control approval and canonical SHA-256 manifest digest | Signed provenance, trusted reviewer identity, tamper-evident audit storage |
| Malicious tool descriptions | Block common injection patterns, only human-approved descriptions | Human review, contextual hardening and Runtime output-injection defenses |
| Malformed payloads | Recursive closed typed schemas with size/depth limits | Full versioned JSON Schema artifact resolver, per-operation contract tests |
| Replay/rollback/stale versions | Immutable manifest versions, irreversible revocation, tenant registry digest | Persistent transactions, integrity proofs, runtime pin/revalidation and idempotency |
| Availability/DoS | Candidate cap 256 and bounded exact search 250k nodes, registry records cap 10k | Per-tenant quotas, inbound size limits, monitoring, capacity tuning |

**Data retention:** synthetic fixtures only. In-memory manifests/audit vanish on process restart. No user files, secrets, personal data or customer payloads are persisted. Production retention/storage schema await owner approval. **Rollout:** standalone synthetic tests → Maven contract/JWT tests → owner ADR ratification → threat review and persistence design → shadow Builder pilot → independent end-to-end approval. **Rollback:** keep adapter disabled (no configured trust anchors) and revoke unsafe tool versions; never reuse revoked digests.

## Requirement evidence / open tasks

| Requirement | Evidence | State |
|---|---|---|
| AF-REQ-003/004 (T02) | draft/approve/revoke/digest/version tests | Component verified; production evidence open |
| AF-REQ-020 (T14) | tenant/scopes/SSRF/injection/risk/veto tests | Component verified; pen test open |
| AF-REQ-029 (T21) | exact RFQ set cover, missing permission, 30 alternatives, incompatible versions | Component verified; Builder integration open |
| AF-REQ-041 | recursive schema and explicit version pins | Typed subset verified; full external JSON Schema validation open |
| T00 | Owner ADR-0002 ratification | **BLOCKED**, not agent-approved |
| HTTP boundary | JUnit `RegistryHttpTest`, `RegistryAuthorizedHttpTest`, `RegistrySecurityTest` | Implemented, Maven tests not executed |

Local task/design delta: [`spec/WORKSTREAM_03.md`](spec/WORKSTREAM_03.md). No changes were made to shared `openspec/**`, `AGENTS.md`, `docs/parallel/**`, or other agent-owned code.

## Offline Builder/Registry fixture contract check

The standalone runner also executes `tests/tool-registry/verify_fixtures.py` (Python 3 standard library only). It validates every fixture digest against an independent implementation of the Java UTF-16-length-prefixed SHA-256 canonicalization, detects scope/tenant/description tampering, and verifies that the allowed synthetic RFQ operation set is the exact least-authority three-operation cover with no payment tool. This detects stale JSON fixtures even when in-memory Java tests remain green. It does **not** prove the live Builder adapter or MCP endpoints work.

## Builder v0 integration compatibility (PROPOSED)

The actual Agent Builder port in `agent/04-agent-engine` requires `approved=true`, accepts only low/medium/high risk, and has no `operation` field in its binding. The raw Registry manifest response is **not** a drop-in Builder input.

This workstream now exposes `GET /v0/registry/builder/manifests` as a read-only adapter for approved, authorized, tenant-scoped `execute` operations below critical risk. It does not grant any scope; any other operation is excluded and a catalogue above 18 eligible operations fails closed with `BUILDER_PORT_CAPACITY`. Java projection tests and OpenAPI describe the temporary bridge. Spring HTTP/JWT tests are **written but not run** pending Maven dependencies and approved architecture.

The remaining `operation` pinning and runtime revalidation gap is documented in `CONTRACT_CHANGE_REQUEST.md`. No claim of a live Builder integration or production MCP attestation is made.
