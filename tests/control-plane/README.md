# Control Plane — executable evidence

## Verification (2026-10-27, local)

```bash
cd <repository root>
bash tests/control-plane/run-core-tests.sh
```

Earlier baseline run (before this revision): OpenJDK 21, `javac -Xlint:all -Werror`, **26/26 PASS** as previously recorded. **The current 36-scenario GitHub revision has not been executed end-to-end in this environment.** A local subset with the new malformed-event case completed **31/31 PASS** under OpenJDK 21; these are not evidence for all 36 current scenarios. Do not treat earlier evidence as proof of the changed code. All fixtures are synthetic; no production data or secrets.

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

The inbox uses event_id + event-content fingerprint; duplicate delivery is idempotent, but a conflicting payload fails. Old operation events do not clear a newer outbox action. The dispatcher has a bounded retry count and requires receiver idempotency by stable operationId/idempotencyKey. This is at-least-once and **not** a claim of exactly-once effects.

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
- Current exact GitHub revision run status: **NOT RUN**; local 31-test subset: **PASS**. Run `bash tests/control-plane/run-core-tests.sh` on this exact Git SHA.
- The repository's `.github/workflows/sdd.yml` presently runs OpenSpec and Python SDD checks **only**. A passing SDD check does not establish Java compilation or API/security integration.
