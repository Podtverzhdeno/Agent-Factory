# Registry workstream security review — 2026-10-27

Status: **component-level security checks executed; service-level certification blocked**.
No independent security audit, live MCP penetration test or production OAuth2/OIDC attestation has been performed.
This file is scoped to workstream-03 and is not a replacement for canonical OpenSpec or owner ADR approval.

## Threat model

**Assets:** tenant-scoped tool capabilities; pinned manifest digest/version; trusted input/output schema references; reviewer approvals; JWT principal and authorization scopes; audit history. No runtime credentials belong in the manifest or its API.

**Attackers:** compromised/rogue MCP publisher with `registry:register`, tenant actor who lacks approval or tool permissions, attacker supplying a malicious tool description/payload/endpoint, misconfigured OIDC issuer or JWKS service, and a stale Builder cache.

**Trust boundaries:** JWT issuer -> authenticated principal -> registry role/scopes -> independently provisioned trust roots (schemas, endpoint, provenance) -> approved manifest -> Builder binding -> downstream Runtime. Registry never proves that an MCP operation actually performs its declared business effect: independent runtime sandbox/effect enforcement remains mandatory.

| Abuse case | Current deterministic prevention | Unverified/dependent control |
| --- | --- | --- |
| `registry:register` self-asserts provenance | Immutable manifest must reference exact out-of-band trusted provenance allowlist. Default application starts with **empty** schema/endpoint/provenance roots. | Independent signed provenance and external endpoint attestation |
| Cross-tenant discovery or mutation | Per-tenant catalog keys; authorization tenant from JWT; foreign records not included in denials; tenant-local audit/revision | Real identity provider and durable PostgreSQL RLS |
| Creator self-approves, retries old digest | Maker/checker, immutable versions, single transition APPROVED -> REVOKED | Durable transactional event store and nonrepudiation |
| Tool description prompt injection | Suspicious description patterns rejected, bounded length and closed manifest structure | Human review and Runtime instruction/data separation |
| Network SSRF/DNS rebinding | No URL/transport execution in registry; only preapproved artifact refs; issuer/JWKS allow HTTPS same-host public-style hostname | Network egress isolation, DNS/IP pinning and independent OIDC trust anchor |
| Permission escalation | Exact JWT scope inclusion plus side-effects/risk checks; Builder receives proposal, no new permission | Runtime per-call authorization, customer consent, action confirmation |
| Incompatible tool versions | Same selected tool ID can only have one version; explicit pins are enforced where supplied | Builder revalidation of manifest revision at run time |
| Tool-candidate explosion | Exact search with hard candidate/node limits; returns BLOCKED when exhausted | Per-tenant request/rate/memory caps |
| JSON zip bomb / deep nesting | Recursive 12-level/512-item/8192-char typed-shape limits after JSON parsing | **HTTP layer** byte cap, parser depth limits, load/DoS tests |
| Credential leakage in payload/trace | No values persisted into audit, manifests forbid common secret/injection patterns | Central redaction, access logs policy, egress controls |

## Secure code / clean-architecture checks

- Domain classes (`ToolRegistry`, `MinimumCapabilityCover`, `PayloadShapeValidator`) import only JDK APIs; no Spring, MCP client, network I/O or database coupling.
- Transport controllers/Jackson/JWT live separately under registry Spring adapter files. No runtime `MCP` connection is initiated.
- Immutable DTO records defensively copy collections; synchronized in-memory mutations are atomic **within one instance** only. No claim of multi-node transactional safety.
- Minimum-set selection minimizes operation count first, total risk second, **distinct** scope grants third, side-effect count fourth, and then deterministic ID tie-break.
- Foreign records are not serialized into denial codes; cross-tenant revisions and audit sequence numbers are tenant-local. Invalid caller subjects containing control and bidi spoofing characters are rejected.
- Versions never mutate approved payload; revocation changes eligibility and invalidates tenant-specific registry revision.

## Executable evidence

From the parent repository root:

```bash
bash tests/tool-registry/run.sh
```

This executes three deterministic suites (component, negative regressions, property oracle) and concurrency checks in Java 21. For fail-on-warning JDK compilation use `javac -Xlint:all -Werror` with sources listed in `tests/tool-registry/run.sh`.

Spring HTTP/Jackson/JWT checks are authored at `src/test/java/...` but **cannot be reported as passed** without Maven/Spring dependencies:

```bash
mvn -f services/tool-mcp-registry/pom.xml verify
```

## Blocking release gates

1. Owner-authored/ratified ADR-0002 for service architecture, datastore ownership, external auth and deployment (currently PENDING).
2. Maven unit, MVC, and OAuth2 integration suite; signed JWT rotation/revocation tests and strict request-size limits.
3. Independent attestation of schemas/endpoints/provenance and live MCP sandbox/egress checks.
4. PostgreSQL transactional audit, backup/restore, retention, tenant policy/RLS, concurrency/fault injection and independent security review.
5. Consumer-driven contract test with Builder and per-call Runtime approval/revalidation, including a negative payment path.

**Decision:** production release must remain BLOCKED until each gate has directly observable evidence. Passing pure Java tests is not proof of secure deployment.

## JSON v0 wire-format and input parser hardening (2026-10-27)

- The frozen OpenAPI contract uses lowercase `risk_level` and `side_effects`. Following the Jackson 3 migration, `RegistryJsonConfig` now registers **type-specific** serializers/deserializers for `Risk` and `Effect` only. `Status`, `Health`, `Decision`, and denial codes preserve their explicitly uppercase wire values. The pure Java enum `toString()` and manifest SHA-256 canonicalization are unchanged.
- Jackson rejects unrecognized or non-lowercase risk/effect values as typed databind exceptions; no default permissions or effect classes are inferred.
- The JSON parser is configured with duplicate-field detection, max 16 nested levels, max 1 MiB document, 50,000 tokens, 8,192-character string, 128-character name, and 64-character number. These limits apply before the domain schema validator and are defense-in-depth, not proof that ingress HTTP body streaming is bounded byte-for-byte.
- `RegistryAuthorizedHttpTest` includes serialization/deserialization compatibility, duplicate-key smuggling, excessive nesting and oversized-string negative cases.
- The dependency-free `verify_wire_contract.py` guards all 25 static invariants. **Maven/MockMvc tests are authored but have not been executed on the exact PR HEAD**; these protections must not be marked operationally verified before that gate passes.
