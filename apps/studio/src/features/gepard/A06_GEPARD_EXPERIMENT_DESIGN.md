# A06 — GEPARD experiment and retest design

**Status: PRE-C0 RESEARCH ONLY. No UI implementation or live optimizer claim.** Task STU-T08 / Issue #13. The branch is a specification/research branch, not C0; no lease has been granted.

## Observed backend evidence

The GEPARD adapter on agent/05-quality-engine labels its default backend deterministic mock. It pins tenant/source AgentSpec, limits changed surfaces to system prompt or tool description, bounds candidates, requires separate tuning and validation references, and rejects references named holdout/sealed. Its optional DSPy bridge is exercised with a fake DSPy module in component tests. This verifies invocation shape, not a real GEPA experiment or an improvement in quality.

The Evaluation evidence snapshot records live DSPy/GEPA as skipped unless paid-inference authorization, an approved model gateway and credentials are explicitly provided. Control Plane currently treats optimizer outcomes as candidates and defaults to fail-closed wiring.

## Proposed experiment lifecycle

1. READY_TO_PROPOSE: current baseline digest and server-approved action/budget are available.
2. QUEUED / RUNNING: server returns a stable operation/experiment ID. A lost response is reconciled by idempotency key or receipt; no blind duplicate run.
3. CANDIDATE_PROPOSED: immutable candidate/baseline digests, backend identity/version, allowed changed surface, sanitized diff, attempts and provenance.
4. RETEST_REQUIRED: independent Evaluation must test the exact candidate digest against a pinned policy and dataset revision.
5. RETESTING: authorized sandbox only; production prompt, harness and grants are unchanged.
6. ACCEPTED_FOR_RELEASE_REVIEW: independent retest passes all predeclared hard gates. This is not RELEASED.
7. REJECTED / BLOCKED / INCONCLUSIVE / UNAVAILABLE: explicit non-success outcomes with safe reason and permitted recovery.

These are proposed display states, not claims that upstream services already expose those exact enums. I00/A01 must map actual backend states through a versioned BFF contract.

## Experiment record

Include tenant-scoped immutable baseline reference/digest; candidate reference/digest and patch digest; optimizer backend/version with truthful mock-versus-real classification; changed surface; stable experiment ID; attempts, deadline and bounded budget; tuning/validation refs and revisions distinct from sealed holdout; retest Evaluation run ID; exact candidate digest; evaluator policy and dataset revision; source stamps and completeness; audit/evidence references; measured outcomes with denominator; hard veto; actual spend separate from requested cap; safe errors and allowed actions.

Prompt diffs may expose private instructions, tenant data or secrets. Redaction and read authorization belong server-side, not only in UI styling.

## Budget and recovery rules

- Server policy controls candidate count, metric calls, attempts, deadline, provider/model allowlist and spend cap.
- Requested cap and actual measured spend are separate values. Missing billing provenance means unavailable, not zero.
- A higher cap requires a new authorized, audited request.
- Timeout, lost response or source outage requires lookup of the original experiment; never submit a duplicate paid action blindly.
- Baseline change, permission change, dataset revision change or unsupported backend version invalidates eligibility and needs reconciliation.

## Independent retest invariants

The retest pins candidate digest, baseline digest, dataset revision, evaluator policy, Runtime and tool schema. Sealed holdout never enters optimizer input. A hard safety/tool/effect regression rejects the candidate regardless of average score or cost. Missing signature, external receipt, gold or sufficient sample size produces blocked, unavailable or inconclusive. Candidate edits after retest invalidate old evidence.

## Truthful label matrix

| Evidence | Safe label | Forbidden claim |
|---|---|---|
| Default deterministic backend | Mock optimizer — synthetic candidate | Real GEPA executed |
| Fake injected DSPy | Adapter contract-tested | Real optimization executed |
| Real optimizer without retest | Candidate proposed — retest required | Verified / ready to release |
| Insufficient independent samples | Inconclusive | Equivalent / no regression proved |
| Retest passed without release confirmation | Evaluation passed; release pending | Released / deployed |
| Source unavailable/stale | Unavailable/stale | Zero cost or success inferred from missing data |

## Requests to I00/A01

Freeze typed list/submit/status/candidate-diff APIs, backend/version identity, baseline/candidate digests, approved changed surface, separate data splits, budget vs actual usage, idempotency and receipt semantics, role-based redaction, exact 401/403/409/429/503 behavior and independent retest linkage. A06 must not call internal optimizer services from the browser or promote a candidate itself.

No live optimization, paid inference or production prompt mutation was performed by this research task.