# Trusted Tool/MCP Registry — contract-first prototype

**Status: COMPONENT VERIFIED (Java 21 standalone tests); HTTP/JWT adapter NOT YET VERIFIED; deployment BLOCKED pending owner ADR-0002.** Requirement traceability: AF-REQ-003/004/020/029/041, T02/T21. This is not a runnable external MCP client and does not grant runtime permissions.

## Safe boundary

- Register draft manifest with `schema_version: 0.1`, semantic operation version, typed schema artifact refs, declared capabilities/scopes/effects, tenant allowlist, non-resolvable approved endpoint artifact ref, risk, health and provenance.
- Approval is explicit (`registry:approve` claim), requires independent reviewer (maker-checker) and an already verified endpoint ref; the approved version and its SHA-256 digest cannot be overwritten.
- Selection accepts only authenticated caller tenant and externally issued token scopes; returns deterministic smallest authorized covering set, pinned operation version/digest, registry revision, explanations and typed denials. Zero eligible tools is `BLOCKED`.
- Raw MCP URLs (including `127.0.0.1`, private IPs and metadata endpoints) are rejected: manifests only reference an out-of-band allowlisted `artifact://approved/endpoints/*` identifier. The registry never connects to that endpoint.
- Manifest digest is **integrity only, not a signature or evidence of source authenticity**. Reviewer/provenance and endpoint verification must be independent. Pattern-based description filters are defense-in-depth, not an injection-proof parser.
- Inbound/outbound object payloads are checked against a deliberately restricted object-shape validator (scalar/object/array types, required fields, no extra fields). **Full JSON Schema 2020-12, nested field validation and schema artifact resolution are pending** an approved storage/validation architecture. Never assert arbitrary JSON Schemas are supported.
- Scope claims are never issued, expanded or inferred from business text; payment/destructive operations are excluded unless request explicitly allows side effects/risk and caller already holds corresponding permission. Consequential live effects additionally require human approval at Runtime.
- No raw secrets, untrusted HTTP fetch, tool invocation, production payment or live order is performed.

## Java 21 dependency-free component tests

From repository root:

```bash
bash tests/tool-registry/run.sh
```

Expected output from **executed run**: `PASS: 39 registry assertions across lifecycle, deterministic cover, tenant/scopes, risk/effects, schema, SSRF, versioning and injection`.

## Experimental Spring Boot HTTP adapter (not deployed)

`services/tool-mcp-registry/pom.xml` uses Java 21 and Spring Boot 3.4.7. With Maven dependencies available, run `mvn -f services/tool-mcp-registry/pom.xml test`. Local execution has **not** verified Maven or the Spring HTTP tests (Maven unavailable in execution environment). HTTP endpoints are described in `openapi.yaml`.

By default **every HTTP request is denied**. To enable, a trusted operator must configure `registry.security.issuer-uri`, `registry.security.jwk-set-uri`, `registry.security.audience` using Spring configuration. Validated Bearer JWT contains `sub`, `tenant_id`, and space-separated `scope`. The tenant is taken only from JWT, not JSON. Request-specific tool grants must already be encoded into the JWT by a separate authorization component. No OIDC provider is configured by this prototype.

Example selection (after independently approving the synthetic manifests):

```json
{"required_capabilities":["read_xlsx","catalog_lookup","write_xlsx"], "allowed_effects":["READ","DRAFT_FILE"],"max_risk":"LOW", "pinned_versions":{}, "expected_schemas":{}}
```

Expected: 3 explicitly authorized pinned operations, excluding `payments.charge`. Without `catalog:read`, expect `BLOCKED` with `MISSING_PERMISSION`; missing capabilities report `NO_CAPABILITY`.

## Remaining work / gate

- **Owner ADR-0002 pending:** PostgreSQL ownership, migrations, real endpoint attestation, evidence/audit retention, availability/health reconciler, deployment and inter-service auth topology are deliberately not implemented.
- Current in-memory catalogue resets on restart, only synthetic schema/endpoint refs exist in `RegistryApplication`, schema references are not fetched, and HTTP adapter tests require a Maven-capable CI runner.
- Concurrency is synchronized within one instance only, no multi-node consistency. Selection is exact for at most 18 eligible operation candidates; greater search space fails closed with `SEARCH_LIMIT`.
- For rollout: immutable append-only metadata storage, approval/audit events, enforced egress policy, human trust reviewer and automated dependency/vulnerability/security testing are prerequisites. Rollback: disable HTTP adapter or roll back module; there are no external effects or stored production customer data.

## Requirement-to-test evidence

| Requirement | Component test (RegistrySelfTest) | Status |
|---|---|---|
| AF-REQ-003/004 | draft/approval, version conflict, digest, malicious description, endpoint allowlist | verified Java 21 |
| AF-REQ-020 | tenant separation, effect/risk veto, scope denial, unverified MCP, SSRF | verified Java 21 |
| AF-REQ-029 | RFQ three-capability minimum cover, missing capability / permission, multi-capability minimum | verified Java 21 |
| AF-REQ-041 | schema mismatch and input/output payload shape validation, pinned versions | verified Java 21 |
| T00 (architecture prerequisite) | owner-authored ADR sign-off | blocked |
| HTTP boundary | `RegistryHttpTest` | unverified, Maven not installed |
