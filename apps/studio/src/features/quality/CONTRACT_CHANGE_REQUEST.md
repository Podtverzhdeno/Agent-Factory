# A06 → I00/A01 Contract Change Request

**Status: PROPOSED / NOT APPROVED / PRE-C0.** Task STU-T08 / Issue #13. No frozen A06 BASE_SHA or granted lease exists.

## Why the request is needed

The Studio API/DTO document says its interfaces and endpoints are proposed, not live. A06 must not create functional Quality, GEPARD, Version, Release or Rollback UI until I00/A01 publish versioned public BFF exports and exact action/error semantics. Browser code must not call internal Java/Python APIs or invent source-owned transitions.

## Evaluation

Provide schema version, source/sourceAsOf/revision/completeness/freshness, evaluation run ID, exact candidate/baseline digests, dataset and evaluator-policy revisions, nullable case counts with denominator definition, trusted evidence verification state and role-safe evidence reference, hard veto/reason code, sanitized finding aggregates, effect-proof state, trusted latency/cost units and denominator, and redacted holdout state only.

Commands need stable idempotency and operation IDs, expected revision where applicable, 202 receipt/polling, and safe typed 401/403/409/429/503 responses. Caller-supplied verdict/evidence fields must never override source-owned truth.

## GEPARD

Provide experiment list/submit/status/candidate-diff APIs with baseline digest, allowed change surface, optimizer backend/version, candidate digest, separate tuning/validation dataset revisions, metric-call/attempt/deadline/spend caps, actual usage distinct from requested cap, stable operation ID, safe error and independent retest reference. Only actually verified backends can be labelled real GEPA.

## Versions / Release / Rollback

Separate immutable Version, release eligibility, Approval, ReleaseRecord, command receipt and DeploymentObservation objects. Define source-owned RELEASED/ROLLED_BACK, target environment, terminal vs pending states, approval scope/expiry, expected revision, idempotency and audit references. A successful registry write must not imply deployment activation unless the contract explicitly proves it.

## Ownership

- I00: common DTOs, schema revisions, app skeleton/aliases, routes, common error envelope and integrated E2E.
- A01: authenticated BFF transport, tenant/session authorization, permissions and typed platform adapters.
- A06: presentation/feature-local code only inside the A06 allowlist, after the actual frozen C0 SHA and a coordinator-issued GRANTED lease.
- Backend owners: Runtime signature/effect evidence, Evaluation API, optimizer jobs, AgentStore, release approvals, deployment and rollback authority.
- Project owner: final topology decision. ADR-0002 remains PENDING OWNER DECISION.

## What closes this request

I00/A01 provide versioned schemas and fixtures for success/empty/partial/stale/unknown/unavailable, concrete error semantics, idempotent command reconciliation, source and signer authority, holdout redaction proof, and a pinned C0 BASE_SHA. Until then, screens remain research/read-only; no live optimization/release/rollback is claimed.