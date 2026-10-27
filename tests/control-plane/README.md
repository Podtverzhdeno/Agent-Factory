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
