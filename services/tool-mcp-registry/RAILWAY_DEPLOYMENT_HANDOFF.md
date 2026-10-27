# Railway hosting target — owner-provided infrastructure context

**Classification:** owner-selected hosting destination, **not an approved service topology or deployment authorization**.

## Confirmed Railway destination (read-only inventory, 2026-10-27)

- Dashboard: https://railway.com/project/ed32802c-7f84-47c3-b744-45e1fe2e6236
- Project ID: `ed32802c-7f84-47c3-b744-45e1fe2e6236` (`adequate-respect`)
- Existing environment: `production`, ID `eacbc53d-a71c-4078-ad68-7e85329d2ab4`
- Existing service: `Agent-Factory`, ID `b0239f26-72d9-4a6e-a0d0-9a429ea0f384`
- Existing source: `Podtverzhdeno/Agent-Factory`, branch `main`, Railpack V3 build environment, region `iad`, one replica.
- No service-scoped variables, domains, volumes or databases found in the inspected production environment.

### Current failure: not an application runtime exception

Deployment `90730d91-ec61-434a-84a3-effb584cb764` failed on 2026-10-27 (UTC) in `BUILD_IMAGE`.
Railpack 0.43.0 emitted `Railpack could not determine how to build the app`; the inspected commit
`f60a7ef628625152454b8b848500ea9cc46d2ba8` (`main`) had only `README.md` at repository root.
No startup command or healthcheck was configured. The service is offline.

**Do not solve this by pointing `production` at an unreviewed workstream branch**, fabricating a
`start.sh` that returns success, opening unauthenticated registry endpoints, or promoting an
in-memory catalogue as durable production storage.

## Proposed future Railway mapping — blocked by ADR-0002

1. **Owner ratification**: commit and approve `docs/architecture/adr/0002-microservices.md`
   covering bounded contexts, tenant identity, database ownership, cross-service auth,
   MCP trust authority, and which services (if any) should be publicly exposed.
   The selected Railway *project* may hold multiple isolated services; the existing
   `Agent-Factory` service is not an approved standalone Tool Registry service.
2. **Java CI and security gates**: Maven clean verify on the exact PR HEAD,
   including Spring Boot 4.1.x compilation, MVC, strict JSON parsing, JWT issuer/audience,
   tenant isolation, negative cases, dependency/SBOM scanning. SDD CI alone is insufficient.
3. **Service source** (once authorized): use a dedicated service if the owner chooses that
   topology. A Maven monorepo service must build from `services/tool-mcp-registry`
   (where `pom.xml` is located), not the documentation-only repository root.
   Pin an approved commit, do not track an unmerged draft work branch.
4. **Secrets & network**: configure only independently attested schema/endpoint/provenance
   roots via an approved operator-controlled mechanism; configure trusted OIDC issuer,
   audience and JWKS; keep private service-to-service networking by default;
   deny unauthenticated requests and unapproved egress; never store tokens in Git.
5. **Persistence**: provision and isolate PostgreSQL only after ADR database ownership and
   migrations are approved. Require durable approval/audit semantics, restart and
   concurrency fault-injection, backup/restore and restricted network permissions.
6. **Release**: verify build success, running replicas, private HTTP health, authenticated
   negative/positive requests, tenant separation, and service metrics; record the
   deployment/commit IDs. Roll back on any safety or schema regression.

## Acceptance and current status

| Gate | Observed |
| --- | --- |
| Owner hosting destination nominated | YES: Railway project above |
| Existing service build | FAILED (documentation-only `main`) |
| Approved service topology | NO: ADR-0002 pending owner sign-off |
| Maven/HTTP/JWT on exact PR HEAD | NOT RUN |
| Durable Registry PostgreSQL migrations/audit | NOT IMPLEMENTED |
| Verified MCP endpoint/provenance attestation | NOT IMPLEMENTED |
| Authorized Builder → Registry → Runtime E2E | NOT RUN |
| Production deployment and real healthcheck | NOT DONE |

No Railway settings, domains, services, databases or environment variables were mutated in
preparing this inventory. The supplied project location is a deployment destination only,
not evidence that the Tool Registry is production-ready.
