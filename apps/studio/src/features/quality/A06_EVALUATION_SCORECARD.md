# A06 — Evaluation Scorecard

**Status: PRE-C0 RESEARCH ONLY. No executable UI.** Task STU-T08 / Issue #13. This branch is based on the Studio specification branch, not a frozen C0 SHA. No claim or lease has been granted.

## Findings and authority

Evaluation is an independent source-owned verdict. The optimizer is allowed to propose a candidate, not approve it. Control Plane / AgentStore owns release policy and transition records. Deployment confirmation may be a separate authority. The browser must not mint PASSED, VERIFIED, RELEASED or ROLLED_BACK.

Repository evidence:
- Evaluation README on branch agent/05-quality-engine describes an isolated component proof, not a deployed independent Evaluation API. Production identity, connected Runtime, KMS, live Kafka and real customer datasets remain unverified.
- tests/quality-engine/EVIDENCE.md reports 117 passed, 3 skipped and 93% statement coverage in a local snapshot, but clarifies that the run used locally staged source rather than the exact latest PR head. Real PostgreSQL, LiteLLM and DSPy/GEPA tests were skipped.
- GEPARD README says its default backend is a deterministic mock, not real DSPy GEPA.
- Control Plane README describes fail-closed/mock-backed wiring; publishing an AgentStore RELEASED channel does not itself switch a running runtime.
- Draft integration PR #6 has a useful synthetic Runtime → signed audit → Evaluation → mock candidate retest path, but does not provide real GEPA or Java AgentStore release proof.
- Studio DTOs and route examples remain proposed contracts. ADR-0002 remains PENDING OWNER DECISION.

## Proposed Scorecard

### Reproducibility
Pin the Evaluation run ID, tenant/workspace from trusted session context, exact candidate AgentSpec digest, optional baseline digest, dataset ID/revision/split, evaluator/policy revision, Runtime and tool-schema revisions, source timestamp/revision, completeness and evidence reference.

### Outcome and evidence
- Status comes only from Evaluation: PASSED, FAILED, BLOCKED, INCONCLUSIVE or UNAVAILABLE. Unknown future statuses render unsupported/unavailable, never green.
- Passed / total / excluded counts carry an explicit denominator. Null means unknown, not zero.
- Display safe aggregate findings and a source-owned hard safety veto. A hard veto takes precedence over average quality, latency and spend.
- Evidence must disclose its verification state and binding to the exact tenant, spec digest, dataset revision, case/run and evaluationRunId. A generic URL or client-supplied verification boolean is not sufficient.
- External side effects are verified only through a trusted receipt or source-approved authority. Natural-language model output and a reservation key are not proof.
- Latency and cost need trusted source, observation window, unit/currency, sample count and denominator. Missing/unreconciled billing means unavailable, not zero.
- Hidden holdout exposes only policy-approved redacted aggregates. Never disclose gold rows, expected answers, sealed IDs, private prompts or per-case details that reveal gold.

### Baseline versus candidate
Compare immutable digests on a compatible cohort, dataset split, evaluator policy and environment. Show measured quality delta, denominator and supported uncertainty method. Do not invent statistical significance or call an underpowered result equivalent. Any hard-gate regression rejects the candidate regardless of cost savings. Editing the candidate after retest invalidates that result.

## Presentation state precedence

This is a UI safety proposal, not source policy:
1. FORBIDDEN if current BFF denies access; clear actor/tenant-bound cache.
2. UNAVAILABLE or UNSUPPORTED if source, freshness, schema or verification is not established.
3. BLOCKED if required signed evidence, approved dataset or prerequisite is missing.
4. INCONCLUSIVE if denominator, sample size or comparability is insufficient.
5. FAILED if source reports failure or a mandatory safety gate fails.
6. PASSED only when Evaluation returns it with valid evidence bound to the exact candidate and policy. This still does not authorize release.

## Required negative tests

- Forged evidence flag or fabricated evidence URL cannot yield PASSED.
- Signature invalid, expired/revoked key, wrong tenant/spec/dataset/case/run or replayed evidence is rejected.
- Missing holdout, denominator or required external receipt cannot yield a false success.
- Hidden holdout is absent from details, tables, exports, tooltips, URLs, logs and error messages.
- An old passing evaluation cannot be reused after candidate digest changes.
- Unknown schema/status, stale data, 403 and source outage remain non-success states.
- Tenant switch or grant revocation clears cached protected data.

## Specific I00/A01 questions

1. Freeze a versioned Evaluation DTO including evidence verification state, source stamps, completeness/freshness and nullable counts.
2. Specify who signs each evidence field and where the tenant/spec/dataset/run binding is verified.
3. Define safe 401/403/409/429/503 payloads and operation polling after 202 or lost response.
4. Provide fixtures proving client-supplied state/evidence can never override the source-owned verdict.
5. Keep holdout redaction enforced server-side, including export and error paths.

This report is design evidence only. No A06 UI tests or production E2E are claimed.