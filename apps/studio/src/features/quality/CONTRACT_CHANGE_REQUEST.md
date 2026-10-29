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

## Cross-surface evidence projection — A06/A08 proposal, not approved

A08's proposal to return a server-verified projection instead of exposing the internal cryptographic envelope or a caller-set boolean is accepted. Customer Quality and Ops Evaluation should consume the **same versioned domain semantics** through separate role-scoped views; do not build competing evidence models.

Suggested public projection (illustrative field names, not a frozen DTO):

- `schemaVersion`.
- `verificationState`: `VERIFIED | UNVERIFIED | INVALID | EXPIRED | REVOKED | UNAVAILABLE | UNSUPPORTED`, set by the independent Evaluation verifier/service.
- `subject`: opaque evaluation-run reference, runtime-run reference where permitted, exact candidate/spec digest, dataset revision/digest where disclosure policy permits, and evaluation-policy revision. The verifier must also bind the trusted tenant internally; never accept a tenant binding supplied by the browser and do not return cross-tenant existence details.
- `verifier`: verifier/source revision and checked-at/source-as-of timestamps.
- `safeReasonCode`: a bounded, documented value such as `MISSING_EVIDENCE`, `VERIFIER_UNAVAILABLE`, `EVIDENCE_REJECTED`, `EVIDENCE_EXPIRED`, `EVIDENCE_REVOKED`, `SUBJECT_MISMATCH`, or `UNSUPPORTED_EVIDENCE_VERSION`. Do not return key material, private payloads or detailed security diagnostics to ordinary operator roles.
- `evidenceRef`: optional and included only when safe for the caller's scope.

Keep **verification outcome** separate from **disclosure outcome**. The BFF/policy layer may return an independently versioned decision such as `AGGREGATE_ONLY | REDACTED_NON_HOLDOUT_REFERENCES | HIDDEN`, plus policy revision and a safe reason. It must not rewrite `verificationState`, calculate thresholds in the browser or send hidden rows and raw suppression thresholds to the UI. Default operator visibility is aggregate-only; redacted non-holdout references require an explicit source-authorized projection.

### Responsibility boundary

- Runtime signing/key authority: signer identity, signature provenance and key lifecycle.
- Independent Evaluation verifier/service: cryptographic validation, replay/expiry/revocation checks, exact run/spec/dataset/policy binding and authoritative Evaluation/evidence-verification outcome.
- Evaluation/data-vault or data-governance owner: case/holdout disclosure policy and cohort-suppression decision.
- A01/BFF: trusted session/tenant checks, server-side authorization and delivery of the permitted projection.
- A06: domain semantics and customer Quality presentation; A08: operator presentation. Neither UI computes, overrides or repairs source outcomes.
- I00: versioned shared DTO/export and integration-test freeze.

### Required contract tests

1. Valid signed evidence with exact subject binding yields source-authored VERIFIED.
2. Wrong tenant, run, spec digest, dataset revision or policy revision; replayed evidence; invalid signature; expired/revoked signer; unsupported schema; and verifier outage never become VERIFIED/PASSED.
3. Ordinary operator role cannot obtain raw holdout rows, gold answers, private prompts, raw traces, hidden IDs or detailed security causes via JSON, deep links, filters, charts, exports, logs or stale cache.
4. Cohort suppression is applied consistently by the owning service/policy, is version-stamped, and cannot be bypassed by repeated filtering or small-cohort drill-down.
5. Cross-tenant and revoked-grant tests return authorization-safe responses without leaking resource existence; source verification state is not confused with caller visibility.

No verified cohort-suppression endpoint or live signature verifier was established at the reviewed C0-R/source evidence. Owner, endpoint, schema, commit and passing negative-test run remain required evidence; this proposal does not imply they already exist.


## Concrete shared DTO proposal for I00/A01 — illustrative only

The following is a **schema proposal**, not a current compiled/live type. I am proposing the semantic contract; I00/A01 must choose the canonical exported names and runtime validation.

```ts
type EvidenceVerificationState =
  | "VERIFIED"
  | "UNVERIFIED"
  | "INVALID"
  | "EXPIRED"
  | "REVOKED"
  | "UNAVAILABLE"
  | "UNSUPPORTED";

interface EvidenceSubjectProjection {
  evaluationRunRef: string;       // opaque and tenant-scoped
  runtimeRunRef: string | null;   // omit/redact where not permitted
  agentSpecDigest: string;
  datasetRevision: string;
  datasetDigest: string | null;   // only where disclosure policy permits
  evaluationPolicyRevision: string;
  // Tenant binding is verified server-side; do not accept or echo a client-selected tenant.
}

interface EvidenceVerificationProjection {
  schemaVersion: string;
  verificationState: EvidenceVerificationState;
  subject: EvidenceSubjectProjection;
  verifierSourceRef: string;
  verifierRevision: string;
  verifiedAt: string | null;
  sourceAsOf: string | null;
  safeReasonCode: string | null;
  evidenceRef: string | null;     // only when authorized and safe for this role
}

type EvidenceDisclosureMode =
  | "AGGREGATE_ONLY"
  | "REDACTED_NON_HOLDOUT_CASES"
  | "UNAVAILABLE";

interface EvidenceDisclosureProjection {
  mode: EvidenceDisclosureMode;
  policyRevision: string | null;
  safeSuppressionReasonCode: string | null;
}

interface HardGateProjection {
  outcome: "CLEAR" | "VETO" | "UNKNOWN";
  safeReasonCode: string | null;
  policyRevision: string;
}
```

Normative semantics for review:

- A value of VERIFIED is source-authored and may be emitted only after signature/key lifecycle, expiry/revocation, replay protection, and exact run/spec/dataset/policy binding succeed for the trusted tenant context. The browser's request cannot select or override that context.
- The subject tuple is the same across Customer Quality and Ops Evaluation. BFF role policy may redact optional references/digest fields, but it must not change the meaning of the verification state.
- Verification and disclosure are separate. A verified artifact can still be undisclosable to a particular operator. In that case retain the source verification result where safe, return aggregate-only or unavailable case detail, and never infer that the user is forbidden from seeing an agent's existence if that would leak cross-tenant data.
- A hard veto should be represented as a categorical, source-owned outcome plus a **safe** reason code. Detailed policy/sealed-case diagnostics belong only in a separately authorized audit surface; never return hidden gold or raw protected reasons to normal UI.
- Case visibility/suppression is decided server-side and version-stamped. No UI threshold, local filter or export path may bypass it.

## Owner still required for cohort suppression

No reviewed source proved an existing cohort-suppression endpoint. I00 must name the actual Evaluation/data-vault/data-governance service owner; that owner defines and tests the versioned policy API. A01 owns BFF transport and authorization mapping; A06 proposes the domain/UI semantics; A08 consumes the operator projection. Until the owner, endpoint/schema, commit and passing small-cohort/holdout leakage tests are linked, treat case disclosure as unavailable and do not assign an arbitrary threshold in Studio.
