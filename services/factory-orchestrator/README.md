# Agent Factory — Control Plane (workstream 01)

**Status: mock-backed domain implementation.** Contracts v0.1 are PROPOSED. ADR-0002 is **PENDING OWNER DECISION**; this folder does not establish a ratified deployable microservice boundary.

## Vertical slice

```text
Authorized Start + immutable READY Snapshot
  -> BUILDING   --direct BuildClient command via outbox-->
  -> TESTING    --independent EvaluationClient command-->
     | safety veto / no holdout / pinned version conflict -> BLOCKED
     | fail with retries/time/spend left -> OPTIMIZING
       --direct OptimizationClient(GEPARD)--> RE_TESTING
       --independent EvaluationClient--> VERIFIED
     | PASS + full evidence -> VERIFIED
  -> RELEASED (low-risk policy or human approval)
  -> ROLLED_BACK (explicit approval)
```

Events are **outcomes only**. Merely consuming an event cannot initiate a new build. A new build requires an authenticated, tenant-scoped Start command, a READY snapshot and immutable digest. Commands are enqueued in the same local aggregate update; `OutboxDispatcher` sends them directly through typed ports. The connector must implement idempotent receiving endpoints. Unknown MCP tools, new permissions, customer files and live effects are never authorized here.

## Contract surfaces

- `Ports.TaskSnapshotReader`: immutable, READY, tenant-scoped snapshot (02)
- `Ports.BuildClient`: typed direct Builder command (04)
- `Ports.EvaluationClient` and `Ports.OptimizationClient`: independently initiated commands (05)
- `Ports.SoupClient`: separate, rights-approved experimental command; not triggered by GEPARD
- `Ports.TenantAuthz`, `Ports.ApprovalReader`, `Ports.ReleasePolicy`, `Ports.TimeSource`
- `Ports.WorkflowLedger`: transaction-local inbox, workflow and outbox port
- `AgentStore`: tenant-scoped immutable version metadata and controlled channel promotion

Current adapters `InMemoryWorkflowLedger` and `InMemoryAgentStore` are **not durable**. A real Postgres implementation needs an owner-ratified data boundary, migrations, event-id uniqueness, atomic domain/outbox transactions, row locking and crash recovery. Cross-module atomicity between WorkflowLedger and AgentStore is not implemented; reconcile it before pilot use.

## Java and Spring Boot

- Java 21, Spring Boot 3.5.6, JWT resource-server dependency, REST controller and OAuth2 security.
- `SpringWiring` intentionally provides a fail-closed TaskSnapshotReader, manual approvals deny-all, low-risk auto promotion deny-all, and **no live clients or publisher**. Production ports must be configured explicitly and reviewed.
- JWT's validated `tenant_id` and `scope` claims drive domain authorization; no trusted X-Tenant header. Resource server requires trusted issuer/JWK configuration outside code. Endpoint startup, JWT integration and database-backed behavior are **not yet verified** in this isolated workstream.
- `pom.xml` includes AgentStore sources as a *local build source* without making a final deployable decision.

## Component test command

From repository root: `bash tests/control-plane/run-core-tests.sh`

The script runs `javac -Xlint:all -Werror` followed by an executable Java component suite without external services or Maven, using synthetic fixtures. A locally mounted subset with 35 scenarios passed under OpenJDK 21 on 2026-10-27; the exact current GitHub PR revision remains unexecuted end-to-end. No production E2E is claimed.

## Release gates

A candidate must include cryptographically formatted spec/tool/model digests, authorized evaluation metadata, immutable baseline digest, dataset ref, independent holdout evidence ref, trace, metrics, verified tool effects, non-regression, and zero safety hard vetoes. Risk HIGH requires external approval. All release and rollback actions are tenant-scoped and audit-visible. An `artifact://` string is a reference, not a content-addressable storage verification — checking real bytes/signatures belongs to the storage/evaluation adapters.

## Threat review / open blockers

1. **ADR-0002 PENDING** — cannot establish service topology, database ownership, transaction strategy or deployment as approved.
2. **Durability BLOCKED** — the in-memory ledger/store lose state on restart; PostgreSQL migrations, transactional inbox/outbox and reconciliation remain to implement after topology ratification.
3. **Upstream clients mocked** — no proof of independent evaluator ACL, sealed holdout, Builder tool correctness, released A2A endpoint or GEPARD gains.
4. **API not integration-tested** — no local Maven artifacts/cache or running issuer; validate actual Spring Boot build, JWT policy, OpenAPI and load behavior in CI.
5. **Outbox is at-least-once** — no exactly-once external effects. Concurrent dispatcher leasing, dead-letter handling, durable delivery and typed remote HTTP errors remain.
6. **Optional Soup completion** — the command and typed completion/re-evaluation route exist only with mocks; no real training backend or rights authority has been tested.
7. **No automatic runtime traffic switch** — publishing `AgentStore.Channel.RELEASED` does not deploy or reload a live Python agent until a separately authorized runtime adapter exists.

For contract changes propose them in this module or PR; do not edit frozen shared specifications. See `tests/control-plane/README.md` for requirement-to-test evidence.

## Safety hardening, workstream 01 (2026-10-27)

- Evaluation events carry a run ID and digest but **cannot authorize release merely by asserting** `independent=true`. `EvidenceVerifier` is a typed upstream-attestation port. Production Spring wiring **denies all** until an explicitly verified upstream adapter is supplied.
- Terminal Evaluation errors for absent approved connectors, unavailable sealed holdout or unauthorised side effects stop repair and require review.
- Separate `SoupFinished` completion returns a pinned model-route and immutable spec revision into independent `RE_TESTING`; GEPARD event cannot stand in for Soup completion.
- Outbox dispatcher ignores historical actions and actions outside their permitted workflow stage, even if their receipts remain pending.
- Four additional synthetic tests cover these controls; no real Evaluation provenance service or training backend is claimed.

## Local hardening status (2026-10-27)

- Tenant and operation identifiers use typed composite keys (no delimiter-concatenation collision).
- AgentStore candidate idempotency compares the complete immutable metadata, including pinned tool digest and evaluation evidence.
- Caller and event publisher permissions are separate: `factory:events:build`, `factory:events:evaluation`, `factory:events:optimization`, `factory:events:soup`.
- Event-driven auto-promotion only follows newly processed Evaluation outcomes, never stale or duplicate events.
- All success paths through Soup are re-evaluated independently before promotion. The `/train` command accepts a tenant-scoped idempotency key.
- Dispatcher refuses obsolete actions after terminal transitions; it remains at-least-once and needs durable leasing/reconciliation in a ratified design.
- The REST contract with request/response schemas is in `openapi/control-plane-v0.yaml`.
- **No current core-suite or Spring/Maven verification claim.** The repository CI only runs SDD checks; execute the suite on the current commit before merge.

## Lifecycle notifications and risk controls

- `LifecycleEventDispatcher` publishes tenant-bound versioned transition notifications through a typed `Ports.OutboxPublisher`. Stable event IDs allow consumer deduplication; acknowledgments are retained in the test ledger. It never triggers Builder.
- State-change audit and pending notification progress are co-located in the in-memory aggregate. The adapter does **not** provide crash durability or transactional Kafka delivery across processes.
- Duplicate event payloads are compared structurally rather than by their string presentation.
- AgentStore rejects HIGH-risk automatic promotion even if the caller supplies a manual approval scope.
- The local mock-backed 35-test subset passed; **do not** infer full PR Java CI, Spring Boot, or production integration success.

## Optional PostgreSQL durability proof (NOT a ratified topology)

The following adapters are opt-in and isolated to this workstream:
`JdbcWorkflowLedger`, `JdbcAgentStore`, `JdbcTransactionScope`, `JacksonStateCodec`.
`db/migration/V1__control_plane_poc.sql` defines tenant-scoped keys, candidate versions,
transition history and workflow-persisted event inbox, command outbox and notification cursor.
No other service database is accessed.

- Default Spring Boot startup intentionally excludes automatic DataSource configuration and
  keeps fail-closed in-memory wiring. JDBC requires explicit `jdbc-poc` profile and an
  isolated PostgreSQL datasource configured with `spring.datasource.jdbc-url`,
  `spring.datasource.username`, `spring.datasource.password`.
- **Schema migration is not automatically applied to production.** The test suite applies
  forward-only V1 then V2 to an ephemeral PostgreSQL Testcontainer. Production migrations, DDL ownership,
  database topology and deployment still await ADR-0002 owner ratification.
- WorkflowLedger and AgentStore must share **one** `JdbcTransactionScope` instance.
  A nested SQL/domain failure marks the transaction rollback-only; a caught nested exception
  cannot allow the outer transaction to commit.
- Metadata request fingerprints use canonical SHA-256, stable across map/set ordering,
  JSON codecs and process restarts. Stored row identities are checked after deserialization.
- The proof-of-concept relies on row locking and replay-safe command IDs. It **does not**
  implement distributed command leases, production-approved Builder/Evaluation/GEPARD endpoints, live
  runtime switching or broker-level exactly-once effects.

### Strict acceptance commands

```bash
# From repository root: JDK 21 + Maven + Docker-capable host
bash tests/control-plane/run-acceptance.sh
```

The script refuses to report PASS if Maven or Docker/PostgreSQL is unavailable, or if
the PostgreSQL integration test report is absent or skipped.

**Verified locally on exact GitHub blob SHA files, OpenJDK 21:
3/3 JDBC transaction tests + 4/4 canonical event fingerprint tests PASS.**
The exact PR head's full component suite, Spring MockMvc JWT suite and PostgreSQL
Testcontainers suite are **not yet executed in this environment**: Maven, Docker and
GitHub checkout network are unavailable. Do not interpret passing SDD validation as Maven PASS.

## New: direct HTTP and tenant-wide PostgreSQL inbox

- Typed outbound HTTP clients for Builder (`/internal/builds`), Evaluation (`/internal/evaluations`) and GEPARD (`/internal/optimizations`) are implemented in `RemoteHttpClients`. They use Java HTTP transport via Spring RestClient, strict HTTP 202 receipts, client/service tokens injected by port, idempotency and correlation headers, HTTPS host allowlist and disabled redirects.
- `RemoteProofOfConceptConfiguration` is enabled only with `remote-poc` profile **and** `factory.remote.enabled=true`. It requires explicit HTTPS endpoints, `factory.remote.allowlisted-hosts` and a separately provisioned `RemoteHttpClients.ServiceTokens` bean; no unauthenticated fallback is provided.
- `RemoteHttpIntegrationTest` exercises the complete Builder → Evaluation FAIL → GEPARD → Evaluation PASS → gated release workflow across three distinct synthetic HTTP servers, plus denied outbound metadata-service/network access. It is **not** a successful test against the independently deployed 04/05 services.
- Forward-only V2 migration adds `cp_event_inbox` with `PRIMARY KEY(tenant_id,event_id)`. `JdbcWorkflowLedger` inserts event fingerprints in the **same transaction** as workflow state/outbox changes, rejecting reuse across distinct workflows. `JdbcPersistenceIntegrationTest` adds the cross-workflow collision scenario.
- `JdbcAgentStore` persists the exact historical rollback response, so repeating a rollback ID is stable even after further version changes.
- Proposed compatibility updates are in `CONTRACT_CHANGE_REQUEST.md` for the owner and upstream service leads. Frozen shared contracts remain unchanged.

### Reproducible local acceptance
Run `bash tests/control-plane/run-acceptance.sh` on the exact PR SHA with **JDK 21, Maven, Docker and access to Maven Central**. It executes the full core and Spring Boot suites, including real PostgreSQL via Testcontainers, and refuses to pass if these are skipped. Java full-suite PASS, Spring/JWT PASS, PostgreSQL PASS and real 04/05 interoperability **have not been observed** on the current PR SHA in this environment.
