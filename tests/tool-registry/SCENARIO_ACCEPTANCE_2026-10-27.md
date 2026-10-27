# Tool/MCP Registry — executed scenario acceptance (2026-10-27)

**Scope:** Workstream 03; Java 21 dependency-free core plus read-only Railway status/log inspection.
**Not a production E2E certificate.** No live Tool Registry service or public service domain was present in the Railway project at observation time; no real HTTP requests were issued to a registry server.

## Command executed

```bash
bash tests/tool-registry/run.sh
```

Observed local output:

```text
PASS: 40 registry assertions across lifecycle, deterministic cover, tenant/scopes, risk/effects, schema, SSRF, versioning and injection
PASS: 53 additional registry security and lifecycle assertions
PASS: 500 deterministic property cases agree with independent exhaustive cover oracle
PASS: 24-way concurrent registration, approval and revocation linearize exactly once
PASS: Builder v0 projection enforces tenant/scopes, risk compatibility and operation restriction
PASS: RFQ JSON fixture verification (4 SHA-256 digests, 16 integrity checks, minimum authorized cover)
PASS: Java domain architecture boundary (4 modules), JWT-deny-all default, 7 HTTP/OpenAPI path mappings, 11 verified runner source references, Maven dependencies
GATE OPEN: Spring Boot parent 4.1.2 selected; Maven/JUnit/JWT build unverified
```

## Executed synthetic business/security scenarios

| Scenario | Expected behavior | Actual evidence | Status |
| --- | --- | --- | --- |
| RFQ: read_xlsx + catalog_lookup + write_xlsx | Select three pinned least-authority implementations, no payment | RegistrySelfTest and JSON fixture verifier | PASS (local) |
| Missing catalogue scope | Explicit typed deny | RegistrySelfTest: MISSING_PERMISSION | PASS (local) |
| Missing capability | Block, no invented tool | RegistrySelfTest: NO_CAPABILITY | PASS (local) |
| Foreign tenant attempts selection/enumeration | No cross-tenant tool metadata | RegistrySelfTest + RegistryRegressionTest | PASS (local) |
| Request payment without sufficient effect/risk permissions | Block payment tool | RegistrySelfTest: EFFECT_NOT_ALLOWED, RISK_NOT_ALLOWED | PASS (local) |
| Register invalid version/schema/unverified endpoint | Reject invalid manifest | RegistrySelfTest | PASS (local) |
| Inject instructions or tamper manifest digest | Reject | RegistrySelfTest | PASS (local) |
| Independent author/approver, immutable approved version | Reject creator self-approval or duplicate mutations | RegistrySelfTest | PASS (local) |
| Revoke approved tool and validate stale use | Block, typed denial, audit records transition | RegistryRegressionTest | PASS (local) |
| ABA: empty → draft → approved → revoked → new approved version | No identical revision for changed tenant lifecycle state | RegistryRegressionTest, introduced in this revision | PASS (local) |
| Simultaneous 24-way register/approve/revoke | Exactly one state transition per stage | RegistryConcurrencyTest | PASS (local) |
| Minimize unique granted scopes | Independent exhaustive cover oracle agrees | 500 randomized cases + dedicated regression | PASS (local) |
| Builder projection excludes payment, critical risks, unmodelled operations | Fail closed for unsafe projection | RegistryBuilderProjectionTest | PASS (local) |
| Payload schema/data type violations | Explicit rejection | RegistrySelfTest, RegistryRegressionTest | PASS (local) |
| RFQ fixture integrity | Digest parity and tamper detection | verify_fixtures.py | PASS (local) |

## Current Railway integration inventory

- Project: `ed32802c-7f84-47c3-b744-45e1fe2e6236` (`adequate-respect`), `production`.
- `Agent-Factory` Control Plane: `SUCCESS`/online in Railway, deployed independently from `agent/01-control-plane`. Read-only logs show Tomcat startup and successful Maven tests for that module, **not** for Tool Registry.
- `Postgres`: `SUCCESS`/online; **Tool Registry persistence is not installed**.
- `agent04-integration-gate`: `DEPLOYING` at inspection. Its live source commit `0cd81ba28a490250f7b8d105848e12dff0b516c3` has `services/agent-builder/agent_builder/core.py` line 62 containing an unterminated `Field(pattern=...)` string. Railway deploy logs explicitly show `SyntaxError: unterminated string literal` for that path and repeated `/readyz` healthcheck failures. This is an Agent04-owned blocker, not a Tool Registry success.
- No Tool Registry Railway service, public domain, or authorized direct access to its HTTP boundary was observed. No live builder→registry→runtime request could be sent.

## Release blockers (not passed)

1. Real Maven `clean verify`, Boot 4.1.x MockMvc/JWT/Security against the exact workstream-03 branch.
2. Deploy isolated, owner-approved registry service and verify real authenticated HTTP calls. Never silently expose or deploy unratified topology.
3. PostgreSQL-backed transactional registry state, approvals, audit and restart/fault injection.
4. Independent MCP endpoint/provenance attestation, secrets/egress sandbox and security review.
5. Agent04 syntax fix and an independently passing, live Builder → Registry → Runtime E2E that pins operation/version/digest/scopes.
6. Formal approval of owner-only ADR-0002 and a production acceptance review.

**Conclusion:** synthetic domain/security scenarios pass; *live integration is BLOCKED and unverified*. No production Railway configuration was modified during these tests.
