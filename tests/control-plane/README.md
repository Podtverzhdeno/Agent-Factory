# Control Plane — executable evidence

## Verification (2026-10-27, local)

```bash
cd <repository root>
bash tests/control-plane/run-core-tests.sh
```

A **locally mounted worktree subset** of the domain was compiled and run with OpenJDK 21 and `javac -Xlint:all -Werror`: **35/35 PASS**, including structural event-collision detection, risk-gate bypass prevention, and lifecycle notification replay.

**Do not misinterpret this as a run of the whole current GitHub revision:** that revision has additional tests and Spring sources not copied into the mounted directory. The exact PR head must still be checked out and `bash tests/control-plane/run-core-tests.sh` executed on it. GitHub's existing SDD workflow does not compile Java. Synthetic fixtures only, no secrets or production credentials.

## Requirement → task → executable checks

| Requirement | Work packet | Verified scenarios |
| --- | --- | --- |
| AF-REQ-001/002 | 01 builder command | Explicit authorized BuildClient call only; no event-triggered build |
| AF-REQ-010/011 | 01 repair control | Eval fail → GEPARD → candidate → independent re-eval → verified; max retries; spend budget |
| AF-REQ-009 | 01 safety | Safety hard veto blocks, no optimization or release |
| AF-REQ-014/048 | 01 quality gate | Holdout missing, invalid artifact digest, mismatched candidate/eval run, high-risk no auto promote |
| AF-REQ-015 | 01 store | Duplicate command, event collision, stale/out-of-order, at-least-once bounded retries, approval and rollback |
| AF-REQ-020 | 01 tenancy | Cross-tenant read/event/start denied, even for idempotent duplicate |
| AF-REQ-017 | 01 optional Soup | Rights/approval required; independent Soup command; optimizer event impersonation denied |

**Scope of proof:** deterministic control-plane logic with mock remote ports. The real storage transaction, Spring Security behavior and independent Evaluation authority were not exercised. Pending ADR-0002 blocks topology-dependent implementation. Do **not** mark global OpenSpec tasks complete on this evidence alone.

## Replay and failure semantics

The in-memory inbox uses event_id + structurally compared typed event content; duplicate delivery is idempotent, but a conflicting payload fails. Old operation events do not clear a newer outbox action. The dispatcher has a bounded retry count and requires receiver idempotency by stable operationId/idempotencyKey. This is at-least-once and **not** a claim of exactly-once effects.

## Reproduction limits

Tests are deliberately dependency-free. `mvn test`/Spring Boot startup/PostgreSQL/Kafka were **not executed** in this environment; Maven is unavailable. Run them in a dedicated environment after building real adapters and security configuration.

## Safety hardening, workstream 01 (2026-10-27)

- Evaluation events carry a run ID and digest but **cannot authorize release merely by asserting** `independent=true`. `EvidenceVerifier` is a typed upstream-attestation port. Production Spring wiring **denies all** until an explicitly verified upstream adapter is supplied.
- Terminal Evaluation errors for absent approved connectors, unavailable sealed holdout or unauthorised side effects stop repair and require review.
- Separate `SoupFinished` completion returns a pinned model-route and immutable spec revision into independent `RE_TESTING`; GEPARD event cannot stand in for Soup completion.
- Outbox dispatcher ignores historical actions and actions outside their permitted workflow stage, even if their receipts remain pending.
- Four additional synthetic tests cover these controls; no real Evaluation provenance service or training backend is claimed.

## Additional pending-regression suite changes

- Event producer scopes are separated: `factory:events:build`, `factory:events:evaluation`, `factory:events:optimization`, `factory:events:soup`.
- Idempotency compares complete immutable AgentStore metadata and typed tenant-scoped keys, not delimiter-joined strings.
- Explicit Soup command idempotency and independent completion route are exercised.
- Builder completion after the time limit must BLOCK rather than start Evaluation.
- Workflow transaction response revision and blocking audit reason are checked.
- Current exact GitHub revision Java run status: **NOT RUN**; local 35-test subset: **PASS**. Run `bash tests/control-plane/run-core-tests.sh` on this exact Git SHA.
- The repository's `.github/workflows/sdd.yml` presently runs OpenSpec and Python SDD checks **only**. A passing SDD check does not establish Java compilation or API/security integration.

## Lifecycle notification outbox (mock-backed)

- `LifecycleEvent` includes schema version, tenant, workflow, correlation, event ID, occurrence time, old/new state and stable per-workflow sequence.
- `LifecycleEventDispatcher` reads transitions committed to the workflow audit ledger and updates its publish cursor only after the `OutboxPublisher` port returns successfully.
- Two local tests exercise deterministic replay-safe IDs, publisher failure recovery, and the fact that notification publishing does not command Builder.
- This is **at-least-once**. On network timeout after broker acknowledgment the same ID can be delivered twice, requiring consumer deduplication. No Kafka broker or PostgreSQL transaction was tested.
- Regression tests also reject different payloads whose `toString()` collides and HIGH-risk autopromotion even when a manual approval marker is passed.

## Maven/Surefire execution (source-level integration)

`services/factory-orchestrator/pom.xml` uses `build-helper-maven-plugin` to add this directory as Maven test sources. `ControlPlaneComponentSuiteTest` is a JUnit 5 wrapper that calls the same standalone main-based scenarios.

```bash
# From repository root, JDK 21 and Maven installed
bash tests/control-plane/run-core-tests.sh
mvn -B -ntp -f services/factory-orchestrator/pom.xml clean test
```

The first command proves the framework-independent Java domain with `javac -Xlint:all -Werror`. The second additionally compiles the Spring Boot application, and Surefire is now configured to execute the component suite through JUnit. Neither command has been executed on the latest PR commit in the current session. The existing GitHub Actions SDD workflow does not invoke Maven; it cannot be changed inside workstream 01's ownership paths.

Additional regression scenarios cover replaying authorized operations after their original approval is withdrawn, deadline-expired start replay, semantic deduplication of event maps, and typed rejection of null event payloads. These are pending a fresh executable run on the exact PR head.

## Proof status at workstream revision

- **Executed, exact Git blob SHA:** `JdbcTransactionScopeTests` 3/3 PASS
  (`javac -Xlint:all -Werror`, Java 21). Both the production class and test class
  matched GitHub's blob IDs.
- **Executed, exact Git blob SHA:** `EventIdentityTests` 4/4 PASS
  (`javac -Xlint:all -Werror`, Java 21). Both source SHA values matched GitHub.
- **Unexecuted on current PR SHA:** full mock-backed domain component suite,
  Spring Boot + JWT MockMvc suite, PostgreSQL Testcontainers integration suite.
- `run-core-tests.sh` now compiles optional JDBC domain adapters and runs
  both isolated proof suites in addition to `ControlPlaneComponentTests`.
- `run-acceptance.sh` requires Maven + Docker and verifies the PostgreSQL
  integration report did not silently skip. It must be run on the final immutable
  PR commit in a Docker-capable CI environment.
- PostgreSQL integration cases cover persistence across new adapter instances,
  atomic rollback of Workflow and AgentStore on injected failures, captured
  nested-transaction rollback-only, version release/rollback recovery, canonical
  idempotency, tenant and stored-row identity isolation. These cases are committed,
  **but not yet verified by executable PostgreSQL results**.

## JDBC + HTTP adapter integration added after earlier baseline

- `JdbcWorkflowLedger`, `JdbcAgentStore`, `JdbcTransactionScope` and `JacksonStateCodec`: opt-in SQL PoC behind `jdbc-poc`; all data is tenant-scoped; transactions cover state plus inbox/command/notification outboxes and local AgentStore changes.
- Forward-only V1 and V2 migrations; V2 enforces tenant-wide event IDs. Updated Testcontainers tests exercise restart, atomic rollback after injected failure, stable idempotency receipts, tenant isolation and collisions across workflows.
- `RemoteHttpClients` and `RemoteHttpIntegrationTest`: real HTTP transport over three local servers with JWT/token port, request headers, host allowlist, redirect denial, typed 202 receipts, and the full FAILED Evaluation → GEPARD → PASSED Evaluation workflow.
- The independent live Builder/Evaluation/GEPARD services, verified artifact provenance, sealed holdout ACL, live A2A promotion and real Broker are **not** part of this isolated test.
- Run the strict acceptance script on an environment with JDK 21, Maven and Docker. The latest PR SHA **has not passed the full exact-revision suite here** because Maven/Docker are unavailable. Do not mark integrated acceptance complete based on committed tests.

## Late outbox response race (2026-10-27)

The original command relay could overwrite a terminal workflow's `TIME_BUDGET_EXHAUSTED`
reason when the remote service completed after termination. It also marked obsolete
operations delivered if an HTTP acceptance arrived after the workflow changed state.

- `OutboxDispatcher` now checks the *current* aggregate and pending operation under
  `WorkflowLedger.transact` before either acknowledging a receipt or incrementing
  failures. No-op late callbacks do not count as newly delivered work.
- `OutboxRaceTests` covers an obsolete fifth failure, an obsolete successful receipt,
  a Builder failure after moving to Evaluation, permanent authorization rejection, five bounded transient failures, and unchanged normal idempotent delivery. **Executed in the mounted Java 21 subset:
  6/6 PASS** with `javac -Xlint:all -Werror`.
- `JdbcPersistenceIntegrationTest` has new cases for replay after a fresh JDBC instance
  (including fingerprint verification and colliding payload rejection), plus the
  fifth-failure/deadline race under PostgreSQL.
- The current GitHub head's complete suite, Maven/Spring and Docker-based PostgreSQL
  runs remain **UNVERIFIED**. No claim of production readiness follows.

## Atomic auto-release hardening

The low-risk Evaluation completion now calls the release gate **inside the same
`WorkflowLedger.transact` callback** as inbox acknowledgment and candidate
registration. With a shared `JdbcTransactionScope`, workflow revision, candidate
creation and AgentStore promotion either commit together or roll back together.
Manual release/rollback store their accepted idempotency operation IDs in the
workflow snapshot and reject replays using a different key.

Regression tests added:
- `ControlPlaneComponentTests`: auto-release increments exactly one workflow
  revision (and does not duplicate a RELEASED transition)
- `JdbcPersistenceIntegrationTest`: a new adapter instance sees the released
  version and rejects replay with a different release key
- `JdbcPersistenceIntegrationTest`: injected exception after an actual JDBC
  AgentStore promotion forces rollback of Evaluation and candidate, then an exact
  event replay succeeds after creating fresh adapters

These new regressions are **committed but not executed** in this environment;
Maven/PostgreSQL acceptance still requires a Docker-capable CI host.

## Remote error taxonomy (2026-10-27)

`Protocol.RemoteCommandFailure` carries explicit `retryable` state.
`RemoteHttpClients` classifies HTTP 401/403 and malformed/contract-rejected receipts as
terminal, while network/503 and other temporary service failures remain retryable.
`OutboxDispatcher` stops a permanent failure immediately and exposes the exact
non-secret code, without retrying an unauthorized request; transient failures keep
the bounded five-attempt policy. This classification never bypasses the live
pending-operation guard added above.

- **Locally executed:** 6/6 `OutboxRaceTests` plus 36/36 mounted domain scenarios,
  OpenJDK 21, `javac -Xlint:all -Werror`.
- **Committed but not executed here:** local-HTTP 403 and 503 contract tests added
  to `RemoteHttpIntegrationTest`, and all PostgreSQL Testcontainers scenarios.
- **Unverified:** Maven/Spring/JWT integration on current GitHub head,
  real team 04/05 endpoints and owner approval for ADR-0002.

## Evaluation branch compatibility proof — 2026-10-27

The current workstream 05 FastAPI `EvaluationRequestBody` has `extra="forbid"`,
requires `evaluation_run_id` on submission and has seven mandatory JSON keys.

- `EvaluationHttpPayload.from` is an explicit, pure Java HTTP DTO mapper. It
  excludes internal operation/correlation/baseline-digest properties and sets
  `evaluation_run_id` from the exact command operation ID.
- `RemoteHttpClients.evaluator` uses this mapper and refuses a 202 receipt
  carrying a different `evaluation_run_id`.
- The local strict DTO suite `EvaluationHttpPayloadTests`: **5/5 PASS**
  with OpenJDK 21 / `javac -Xlint:all -Werror`.
- Re-ran an isolated mounted JDK subset: **36/36 component, 6/6 outbox races,
  5/5 Evaluation DTO contract = 47/47 PASS**. These are local mounted source
  results, **not a full checkout and test of the current GitHub head**.
- `RemoteHttpIntegrationTest` now validates the strict seven-field JSON shape,
  authenticating header and that mismatched evaluation receipt run IDs fail.
  This Maven test is **not executed locally**.
- Upstream Builder branch has a typed Python handler but no approved HTTP server.
  The GEPARD branch has an optimization adapter but no approved HTTP endpoint.
  Do not assert real upstream HTTP E2E. See `CONTRACT_CHANGE_REQUEST.md` for
  owner-facing compatibility blockers.

The full Spring Boot/JWT/Maven and PostgreSQL Testcontainers acceptance gates
remain open. Local Maven and Docker binaries are unavailable; the GitHub workflow
currently covers SDD only. ADR-0002 remains `PENDING OWNER DECISION`.

## Verifiable unattended acceptance gate

`bash tests/control-plane/run-acceptance.sh` refuses to return PASS if Maven,
Docker, Java, Python or a live Docker daemon is unavailable. Set
`EXPECTED_HEAD_SHA=<40-character Git SHA>` to require execution on a specific
checkout commit.

After Maven `clean verify`, the gate parses Surefire XML with
`verify-surefire.py` and requires exactly one report for each of
`ControlPlaneComponentSuiteTest` (at least 4 JUnit methods),
`ControlPlaneSecurityTest` (at least 6),
`JdbcPersistenceIntegrationTest` (at least 15) and
`RemoteHttpIntegrationTest` (at least 8), with zero errors, failures and
skips. Missing/corrupt/duplicate reports are failures, not a green result.
The standalone `ControlPlaneComponentTests.main` also guards its 48
executed scenarios; a JUnit wrapper alone cannot substitute for those checks.

The gate itself has seven automated self-tests in
`tests/control-plane/test_verify_surefire.py` for successful and deliberately
invalid reports. **These 7 Python self-tests were executed and passed on JDK 21
container's Python environment**; their Git blob SHA values were independently
compared with GitHub. Together with 7 separately executed Java/JDBC/hash
assertions, there are **14 confirmed passing isolated checks**. This does
**not** imply the unexecuted Maven/PostgreSQL/JWT/HTTP integration suites pass.

## Verified follow-up: strict Surefire evidence and malformed receipts

- **2026-10-27, executed locally under OpenJDK 21:** `bash tests/control-plane/run-core-tests.sh`
  produced **36/36 component, 7/7 outbox reliability and 5/5 strict Evaluation
  HTTP DTO tests PASS**, with `javac -Xlint:all -Werror`.
  This is the mounted local subset, **not** a claim of full-suite verification
  at the latest GitHub commit.
- A mismatched `CommandReceipt.operationId` is now
  `RemoteCommandFailure("REMOTE_RECEIPT_MISMATCH", false)`; receiver protocol
  violations are terminal and cannot cause five unnecessary business retries.
  The seventh outbox test covers wrong-operation receipts and no re-dispatch.
- The existing `verify-surefire.py` was strengthened to compare XML testcase
  elements with report totals and per-case skip/failure/error evidence. Its
  `JdbcPersistenceIntegrationTest` minimum was corrected from an impossible
  15 to the **14 actual JUnit test methods** on the inspected revision.
  `RemoteHttpIntegrationTest` minimum was raised to 9.
- **Exact GitHub blob tests executed:** `test_verify_surefire.py` **9/9 PASS**,
  using `python3 -m unittest discover -s tests/control-plane -p
  test_verify_surefire.py -v`; verifier blob
  `d69c556fa1dee79bed9d6428ce5966b6ef1fa1c6` and test blob
  `a8115a88d79f2e0435e5df80759f348b13c05292` matched
  `git hash-object` locally.
- Duplicate alternative validator files were deleted; only the one acceptance
  script and its tested validator remain.
- **Still not executed:** exact-revision Maven/Spring/JWT, actual PostgreSQL
  Testcontainers, full upstream Builder/GEPARD HTTP E2E or independent
  production security approval. Maven and Docker are unavailable in the
  current execution environment. GitHub's SDD validation does not cover Java.
  ADR-0002 remains owner-pending.
